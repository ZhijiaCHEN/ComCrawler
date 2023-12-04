from itertools import zip_longest
import textdistance
import re
import time
import os
from PIL import Image
import textdistance
import psycopg2
from lxml import etree
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from io import StringIO
from datetime import datetime
from bs4 import BeautifulSoup
from selenium.common.exceptions import ElementNotInteractableException, ElementClickInterceptedException, WebDriverException, JavascriptException
parser = etree.HTMLParser(remove_blank_text=True, remove_comments=True, remove_pis=True, default_doctype=False)

SELF_ID = 'data-self-id'
PARENT_ID = 'data-parent-id'
NODE_DEPTH = 'data-depth'
NODE_HEIGHT = 'data-height'
TARGET_FLAG = 'data-target-flag'
STYLE_VISIBLITY = 'data-style-visibility'
STYLE_DISPLAY = 'data-style-display'
STYLE_HEIGHT = 'data-style-height'
STYLE_WIDTH = 'data-style-width'
TOUCHED = 'data-touched'
CLICK_ID = 'data-click-id'
ANCESTOR_TAG = 'ancestors-tag'
ANCESTOR_IDX = 'ancestors-idx'
POSITION = 'data-position'

initScript = open("./init.js").read()

currentPagePath = None

NON_VISUAL_TAGS = ['head', 'script', 'noscript', 'meta', 'link', 'style']
def javascript_init(driver):
    driver.execute_script(initScript)
    iframes = driver.find_elements_by_tag_name('iframe')
    for f in iframes:
        try:
            driver.switch_to.frame(f)
            driver.execute_script(initScript)
            driver.switch_to.default_content()
        except Exception as e:
            # print('javascript_init: {}\n'.format(e))
            driver.switch_to.default_content()

def rect_distance(rect1, rect2):
    left = rect2['right'] < rect1['left']
    right = rect1['right'] < rect2['left']
    top = rect2['bottom'] < rect1['top']
    bottom = rect1['bottom'] < rect2['top']
    def dist(x1, y1, x2, y2):
        return ((x1-x2)**2+(y1-y2)**2)**0.5
    if top and left:
        return dist(rect1['left'], rect1['top'], rect2['right'], rect2['bottom'])
    elif left and bottom:
        return dist(rect1['left'], rect1['bottom'], rect2['right'], rect2['top'])
    elif bottom and right:
        return dist(rect1['right'], rect1['bottom'], rect2['left'], rect2['top'])
    elif right and top:
        return dist(rect1['right'], rect1['top'], rect2['left'], rect2['bottom'])
    elif left:
        return rect1['left']-rect2['right']
    elif right:
        return rect2['left']-rect1['right']
    elif top:
        return rect1['top']-rect2['bottom']
    elif bottom:
        return rect2['top']-rect1['bottom']
    else:             # rectangles intersect
        return 0

tagIdDict = {}
def node_to_tuple(node):
    """
    Convert a node to the following tuple:
    (tagId, (attribId1, attribId2, ..., attribIdN))
    Where tagId is the tag ID of the node, and (attribId1, attribId2, ..., attribIdN) is the list of the attribute IDs of the node in ascending order.
    """
    ret = [tagIdDict.setdefault(node.tag, len(tagIdDict))]
    attribList = [tagIdDict.setdefault(k, len(tagIdDict)) for k in node.attrib]
    attribList.sort()
    ret.append(tuple(attribList))
    return tuple(ret)

def element_to_tuple(element):
    """
    Convert an element to the following tuple by travseing the element with depth first preorder traversal:
    ((tagId1, (attribId11, attribId12, ..., attribId1N)), (tagId2, (attribId21, attribId22, ..., attribId2N)), ..., (tagIdN, (attribIdN1, attribIdN2, ..., attribIdNN)))
    Where tagIdi is the tag ID of the ith visited node, and (attribIdi1, attribIdi2, ..., attribIdiN) is the list of the attribute IDs of the node in ascending order.
    """
    elmList = []
    pre_order_traversal(element, lambda node: elmList.append(node_to_tuple(node)))
    return tuple(elmList)

def tag_test(tags):
    out = 'self::{}'.format(tags[0])
    for i in tags[1:]:
        out += ' or self::{}'.format(i)
    return out

def attribute_test(attributes, ignoreLongString = True):
    out = ''
    testNum = 0
    for k, v in attributes.items():
        if k == 'text': continue
        if k in custom_attrib: continue
        if ignoreLongString and len(v) > 50: continue
        if '"' in v: continue #don't know how to handle "
        v = v.replace('\'', '\\\'')
        out += '@{}="{}" and '.format(k, v)
        testNum += 1
    if len(out) > 0:
        out = out[:-5]
    if testNum > 0:
        return out
    else:
        return None

def merge_dict(dict1, dict2): 
    dict1.update(dict2)
    return dict1 

def pre_order_traversal(roots, visit_function, *args, **kwargs):
    # traverse one or mulitple trees using preorder traversal
    # if roots is a iterable object, all the trees are considered to have the same layout, and for each step on the raversing path a list of corresponding nodes are passed to the visit_function. A None will be passed if a root doesn't have a node at that step.

    # if visit function returns True, stop getting further
    stop = visit_function(roots, *args, **kwargs)
    if stop: return
    if isinstance(roots, list):
        for childItr in zip_longest(*[[] if root is None else root.xpath('./child::*') for root in roots]):
            pre_order_traversal(list(childItr), visit_function, *args, **kwargs)
    else:
        for child in roots.xpath('./child::*'):
            pre_order_traversal(child, visit_function, *args, **kwargs)

def post_order_traversal(roots, visit_function, *args, **kwargs):
    # traverse one or mulitple trees using postorder traversal
    # if roots is a iterable object, all the trees are considered to have the same layout, and for each step on the raversing path a list of corresponding nodes are passed to the visit_function. A None will be passed if a root doesn't have a node at that step.
    if isinstance(roots, list):
        for childItr in zip_longest([] if root is None else root.xpath('./child::*') for root in roots):
            post_order_traversal(list(childItr), visit_function, *args, **kwargs)
    else:
        for child in roots.xpath('./child::*'):
            post_order_traversal(child, visit_function, *args, **kwargs)

    # if visit function returns True, stop getting further
    stop = visit_function(roots, *args, **kwargs)
    if stop: return

def double_traversal(roots, first_visit_function, second_visit_function, *args, **kwargs):
    # each node is visited before and after visiting all of its descendants
    # if roots is a iterable object, all the trees are considered to have the same layout, and for each step on the raversing path a list of corresponding nodes are passed to the visit_function. A None will be passed if a root doesn't have a node at that step.
    first_visit_function(roots, *args, **kwargs)
    if isinstance(roots, list):
        for childItr in zip_longest([] if root is None else root.xpath('./child::*') for root in roots):
            double_traversal(list(childItr), first_visit_function, second_visit_function, *args, **kwargs)
    else:
        for child in roots.xpath('./child::*'):
            double_traversal(child, first_visit_function, second_visit_function, *args, **kwargs)
    second_visit_function(roots, *args, **kwargs)

custom_attrib = [SELF_ID, PARENT_ID, NODE_DEPTH, NODE_HEIGHT, TARGET_FLAG, TOUCHED, CLICK_ID, ANCESTOR_IDX, ANCESTOR_TAG, POSITION]
def compute_similarity(element1, element2):
    #compute the similarity between two trees
    #two trees are only considered similar if:
    #   1. they have the same layout
    #   2. each pair of corresponding nodes are of the same tag
    #   3. they have the same attributes at corresponding nodes
    #   4. they both have or have no text content at corresponding nodes
    #the similarity value is 0 if the two trees are not similar, and 1 if all the corresponding attributes and text content have the same value, and some value between 0 and 1 if some of the attributes and/or text vary.
    argEnvelope = {'abSim':0, 'maxSim':0} # {absolute similarity, maximum similarity}
    
    def compare_attribute(nodePair, argEnvelope):
        node1 = nodePair[0]
        node2 = nodePair[1]
        keys = [k for k in node1.attrib.keys() if k not in custom_attrib]# ignore injected custom attributes
        argEnvelope['maxSim'] += len(keys)
        for k in keys:
            #if node1.attrib[k] == node2.attrib[k]:
            #    argEnvelope['abSim'] += 1
            argEnvelope['abSim'] += textdistance.jaro.similarity(node1.attrib[k], node2.attrib[k])

    pre_order_traversal([element1, element2], compare_attribute, argEnvelope)
    if argEnvelope['maxSim'] == 0:
        return 1
    else:
        return argEnvelope['abSim']/argEnvelope['maxSim']

def tuple_similarity(t1, t2):
    assert len(t1) == len(t2), 'tuple_similarity: the two tuples must have the same length'
    if len(t1) == 0:
        return 1
    sim = 0
    for s1, s2 in zip(t1, t2):
        """
        if len(s1) + len(s2) == 0:
            sim += 1
        else:
            sim += (1 - abs(len(s1)-len(s2))/max([len(s1), len(s2)]))
        """
        if len(s1) > 50 or len(s2) > 30:
            # play some trick on lengthy attributes
            sim += (1 - abs(len(s1)-len(s2))/max([len(s1), len(s2)]))
    
        elif len(s1) + len(s2) == 0:
            sim += 1
        else:
            sim += textdistance.strcmp95.normalized_similarity(s1, s2)
    return sim/len(t1)

def get_bounding_rects(elements, driver):
    script = """
    ret = []
    for (i = 0 i < arguments.length i++) 
    {
        ret.push(arguments[i].getBoundingClientRect())
    } 
    return ret
    """
    return driver.execute_script(script, *elements)

def pick_fixed(elements, driver):
    """
    Picks the position fixed elements
    """
    scrollY = driver.execute_script('return window.scrollY')
    driver.execute_script('window.scrollTo(0, 0)')
    oldY = [r['y'] for r in get_bounding_rects(elements, driver)]
    driver.execute_script('window.scrollTo(0, window.innerHeight)')
    newY = [r['y'] for r in get_bounding_rects(elements, driver)]
    driver.execute_script('window.scrollTo(0, {})'.format(scrollY))
    ret = []
    for i,e in enumerate(elements):
        if abs(newY[i]-oldY[i])< 1:
            ret.append(e)
    return ret

def find_url(string):
    url = re.match('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', string) 
    return url 

def wait_until_body_still(checkInterval, timeout, driver):
    """
    iframes = driver.find_elements_by_tag_name('iframe')
    def count_iframe_elements():
        count = 0
        for f in iframes:
            try:
                driver.switch_to.frame(f)
                count += driver.execute_script('return document.evaluate("count(.//*)", document.body, null, XPathResult.NUMBER_TYPE, null ).numberValue')
                driver.switch_to.default_content()
            except Exception as e:
                print('wait_until_body_still: {}\n'.format(e))
                driver.switch_to.default_content()
        return count
    """
    exceptCnt = 0
    try:
        oldCount = driver.execute_script('return document.evaluate("count(.//*)", document.body, null, XPathResult.NUMBER_TYPE, null ).numberValue')# + count_iframe_elements()
        time.sleep(checkInterval)
        newCount = driver.execute_script('return document.evaluate("count(.//*)", document.body, null, XPathResult.NUMBER_TYPE, null ).numberValue')# + count_iframe_elements()
    except Exception as e:
        oldCount = -1
        newCount = 0
        exceptCnt += 1
        print('wait_until_body_still: {}\n'.format(e))
        #time.sleep(1)
    sleepTime = 0
    while(exceptCnt < 3 and oldCount != newCount and sleepTime < timeout):
        oldCount = newCount
        sleepTime += checkInterval
        time.sleep(checkInterval)
        try:
            newCount = driver.execute_script('return document.evaluate("count(.//*)", document.body, null, XPathResult.NUMBER_TYPE, null ).numberValue')# + count_iframe_elements()
        except Exception as e:
            exceptCnt += 1
            oldCount = -1
            newCount = 0
            print('wait_until_body_still: {}\n'.format(e))
    if sleepTime >= timeout:
        print('wait_until_body_still: wait time out.\n')

def wait_until_element_still(element, checkInterval, timeout, driver):
    exceptCnt = 0
    try:
        oldCount = driver.execute_script('return document.evaluate("count(.//*)", arguments[0], null, XPathResult.NUMBER_TYPE, null ).numberValue', element)
        time.sleep(checkInterval/1000)
        newCount = driver.execute_script('return document.evaluate("count(.//*)", arguments[0], null, XPathResult.NUMBER_TYPE, null ).numberValue', element)
    except Exception as e:
        oldCount = -1
        newCount = 0
        exceptCnt += 1
        print('wait_until_body_still: {}\n'.format(e))
        #time.sleep(1)
    sleepTime = 0
    while(exceptCnt < 3 and oldCount != newCount and sleepTime < timeout):
        oldCount = newCount
        sleepTime += checkInterval
        time.sleep(checkInterval/1000)
        try:
            newCount = driver.execute_script('return document.evaluate("count(.//*)", arguments[0], null, XPathResult.NUMBER_TYPE, null ).numberValue', element)
        except Exception as e:
            exceptCnt += 1
            oldCount = -1
            newCount = 0
            print('wait_until_element_still: {}\n'.format(e))
    if sleepTime >= timeout:
        print('wait_until_element_still: wait time out.\n')

def wait_until_page_loaded(driver, timeout):
    waitTime = 0
    while waitTime < timeout and driver.execute_script('return (document.readyState != "complete")'):
        waitTime += 0.1
        time.sleep(0.1)
    #wait_until_body_still(1, 10, driver)
    if waitTime > timeout:
        print('wait_until_page_loaded: timout.\n')

def wait_until_request_complete(client, checkInterval, timeout):
    waitTime = 0
    oldCnt = len(client.har['log']['entries'])
    time.sleep(checkInterval)
    newCnt = len(client.har['log']['entries'])
    waitTime += checkInterval
    while waitTime < timeout and newCnt != oldCnt:
        oldCnt = newCnt
        time.sleep(checkInterval)
        newCnt = len(client.har['log']['entries'])
        waitTime += checkInterval
    if waitTime > timeout and newCnt != oldCnt :
        print('wait_until_request_complete: timout.\n')
        return (-len(client.har['log']['entries']))
    else:
        return len(client.har['log']['entries'])

def is_newpage(driver):
    return currentPagePath != driver.execute_script('return window.location.pathname')
    # if currentPagePath != driver.execute_script('return window.location.pathname'):
    #     return True
    # else:
    #     return not driver.execute_script('return window.hasOwnProperty(\'isNewPage\');')

def touch_elements(driver):
    try: 
        driver.execute_script('touch_elements();')
    except JavascriptException:
        javascript_init(driver)
        driver.execute_script('touch_elements();')
    iframes = driver.find_elements_by_tag_name('iframe')
    for f in iframes:
        try:
            driver.switch_to.frame(f)
            try:
                driver.execute_script('touch_elements();')
            except JavascriptException:
                javascript_init(driver)
                driver.execute_script('touch_elements();')
            driver.switch_to.default_content()
        except Exception as e:
            # print('touch_elements: {}\n'.format(e))
            driver.switch_to.default_content()

def feedbacks_text(driver):
    ret = ''
    if is_newpage(driver):
        ret += driver.execute_script('return document.body.outerHTML')
    else:
        elms = driver.execute_script('return feedbacks_new_size();')
        for e in elms:
            if e.tag_name in NON_VISUAL_TAGS:
                continue
            if e.tag_name == 'iframe':
                try:
                    driver.switch_to.frame(e)
                    ret += driver.execute_script('return document.body.innerHTML')
                    driver.switch_to.default_content()
                except Exception as e:
                    # print('feedbacks_text: {}\n'.format(repr(e)))
                    driver.switch_to.default_content()
            else:
                try:
                    ret += e.get_attribute('outerHTML')
                except Exception as e:
                    print('feedbacks_text: {}\n'.format(repr(e)))
        #ret += driver.execute_script('return feedbacks_new_size_text();')
        """
        iframes = driver.find_elements_by_tag_name('iframe')
        for f in iframes:
            try:
                driver.switch_to.frame(f)
                if is_newpage(driver):
                    ret += driver.execute_script('return document.body.outerHTML')
                else:
                    ret += driver.execute_script('return untouched_elements_text();')
                driver.switch_to.default_content()
            except Exception as e:
                print('untouched_elements_text: {}\n'.format(e))
                driver.switch_to.default_content()
        """
    return '<html>\n{}\n</html>'.format(ret)

def remove_non_visual_elements(node, pnode):
    if node.tag in NON_VISUAL_TAGS:
        if pnode is not None:
            pnode.remove(node)
        return
    else:
        for child in node.xpath('./child::*'):
            remove_non_visual_elements(child, node)

def click_through_element(elm, driver):
    """
    Try to click an element from itself to all of its decendants until the click is succesfully performed.
    """
    try:
        #driver.execute_script('return arguments[0].click()', elm)
        elm.click()
        return True
    except Exception as err:
        #for e in driver.execute_script('return get_elements_by_xpath("./descendant::*", arguments[0])', elm):
        #    try:
        #        e.click()
        #        return True
        #    except Exception as err:
        #        pass
        return False

def fullpage_screenshot(driver, file):
    driver.execute_script('"window.scrollTo(0, 0)"')
    total_width = driver.execute_script("return document.body.offsetWidth")
    total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
    viewport_width = driver.execute_script("return document.body.clientWidth")
    viewport_height = driver.execute_script("return window.innerHeight")
    #print("Total: ({0}, {1}), Viewport: ({2},{3})".format(total_width, total_height,viewport_width,viewport_height))
    rectangles = []

    i = 0
    while i < total_height:
        ii = 0
        top_height = i + viewport_height

        if top_height > total_height:
            top_height = total_height

        while ii < total_width:
            top_width = ii + viewport_width

            if top_width > total_width:
                top_width = total_width

            #print("Appending rectangle ({0},{1},{2},{3})".format(ii, i, top_width, top_height))
            rectangles.append((ii, i, top_width,top_height))

            ii = ii + viewport_width

        i = i + viewport_height

    stitched_image = Image.new('RGB', (total_width, total_height))
    previous = None
    part = 0

    for rectangle in rectangles:
        if not previous is None:
            driver.execute_script("window.scrollTo({0}, {1})".format(rectangle[0], rectangle[1]))
            #print("Scrolled To ({0},{1})".format(rectangle[0], rectangle[1]))
            time.sleep(0.2)

        file_name = "part_{0}.png".format(part)
        #print("Capturing {0} ...".format(file_name))

        driver.get_screenshot_as_file(file_name)
        screenshot = Image.open(file_name)

        if rectangle[1] + viewport_height > total_height:
            offset = (rectangle[0], total_height - viewport_height)
        else:
            offset = (rectangle[0], rectangle[1])

        #print("Adding to stitched image with offset ({0}, {1})".format(offset[0],offset[1]))
        stitched_image.paste(screenshot, offset)

        del screenshot
        os.remove(file_name)
        part = part + 1
        previous = rectangle

    stitched_image.save(file)
    #print("Finishing chrome full page screenshot workaround...")
    return True

def find_paragraphs(pageEtree):
    pNode = [p for p in pageEtree.xpath('//p[string-length(text()) > 10]|//div[string-length(text()) > 10]')]
    #pNode = [p for p in pageEtree.xpath('//p[string-length(text()) > 10]')]
    def cluster_main_content(elmArray):
        clusterMark = [False]*len(elmArray)
        clusterArray = []
        for i in range(len(elmArray)):
            if (clusterMark[i]):
                continue
            clusterMark[i] = True  
            cluster = [elmArray[i]]
            clusterArray.append(cluster)
            for j in range(i+1, len(elmArray)):
                if (clusterMark[j]):
                    continue
                parent = elmArray[i].getparent()
                while (parent is not None):
                    if parent in elmArray[j].xpath('./ancestor::*'): 
                        p1 = elmArray[i]
                        p2 = elmArray[j]
                        match = False
                        attrib1 = ''
                        attrib2 = ''
                        while ((p1 is not None) and (p2 is not None) and (p1 != parent) and (p2 != parent) and (p1.tag == p2.tag) and (len(p1.attrib) == len(p2.attrib))): 
                            match = True
                            attribVal1 = ''
                            attribVal2 = ''
                            for k in p1.attrib:
                                if k in custom_attrib:
                                    continue
                                if k not in p2.attrib:
                                    match = False
                                    break
                                else:
                                    attribVal1 += p1.attrib[k]
                                    attribVal2 += p2.attrib[k]
                                    attrib1 += k + ': ' + p1.attrib[k] + '\n'
                                    attrib2 += k + ': ' + p2.attrib[k] + '\n'
                            sim = textdistance.jaro.normalized_similarity(attribVal1, attribVal2)
                            if (sim < 0.8):
                                match = False
                            if not match:
                                break
                            else:
                                p1 = p1.getparent()
                                p2 = p2.getparent()
                        if match:
                            cluster.append(elmArray[j])
                            clusterMark[j] = True
                        break
                    parent = parent.getparent()
        return clusterArray

    return cluster_main_content(pNode)
        
def paragraph_text_length(elm):
    ret = 0
    for p in elm.xpath('./child::p|./child::div'):
        if p.text:
            ret += len(p.text)
    return ret

def open_page(driver, url, proxyClient = None, markNewPage=True, scroll=True):
    try:
        driver.delete_all_cookies()
        try:
            driver.get(url)
        except Exception as e:
            print('page loading timeout.')
        if scroll:
            oldPageHeight = 0
            try:
                newPageHeight = driver.execute_script('return document.body.scrollHeight;')
            except:
                newPageHeight = 0

            scrollCnt = 0
            oldScrollY = 0
            newScrollY = 0
            while(scrollCnt < 3 or (newScrollY != oldScrollY and scrollCnt < 10)):
                scrollCnt += 1
                oldScrollY = newScrollY
                try:
                    driver.execute_script("""window.scrollBy({
                                            top: window.innerHeight/2,
                                            behavior: 'smooth'
                                            });""")
                    time.sleep(1)
                    newScrollY = driver.execute_script('return window.scrollY;')
                    if newScrollY == oldScrollY:
                        driver.execute_script("""window.scrollTo({
                                            top: document.body.scrollHeight,
                                            behavior: 'smooth'
                                            });""")
                        time.sleep(1)
                        newScrollY = driver.execute_script('return window.scrollY;')
                except Exception as e:
                    print('open_page: {}'.format(repr(e)))
        driver.execute_script('window.scrollTo(0, 0);')
        #if proxyClient is not None:
        #    wait_until_request_complete(proxyClient, 1, 10)
        #else:
        #    wait_until_page_loaded(driver, 10)
        #javascript_init(driver)
        if markNewPage:
            global currentPagePath
            currentPagePath = driver.execute_script('return window.location.pathname;')
    except Exception:
        pass

def close_other_pages(driver, mainTab):
    if is_newpage(driver):
        for w in driver.window_handles:
            if w != mainTab:
                driver.switch_to.window(w)
                driver.close()   

def elm2etree(driver, elm, parser = parser):
    if is_newpage(driver):
        javascript_init(driver)
    elmHTML = ''
    try:
        elmHTML = driver.execute_script('return arguments[0].outerHTML;', elm)
        elmTree = etree.parse(StringIO(elmHTML), parser)
        iframes = [f for f in elmTree.xpath('//iframe')]
        for f in iframes:
            try:
                attribTest = attribute_test(f.attrib)
                if attribTest is None:
                    #fElm = driver.execute_script('return get_element_by_xpath(\'.//iframe\', document.body)')
                    continue
                else:
                    try:
                        script = """return get_element_by_xpath('.//iframe[{}]', document.body)""".format(attribTest)
                        fElm = driver.execute_script("""return get_element_by_xpath('.//iframe[{}]', document.body)""".format(attribTest))
                    except Exception as e:
                        print(repr(e))
                        continue
                if fElm is not None and driver.execute_script('return !is_element_trivial(arguments[0]);', fElm):
                    driver.switch_to.frame(fElm)
                    fBody = driver.execute_script('return document.body')
                    if fBody is not None:
                        fEtree = elm2etree(driver, fBody)
                        driver.switch_to.parent_frame()
                        if fEtree is not None:
                            fEtree = fEtree.getroot()[0]
                            #fParent = f.get_parent()
                            #fParent.remove(f)
                            for fChild in fEtree:
                                if fChild.tag in NON_VISUAL_TAGS:
                                    continue
                                fEtree.remove(fChild)
                                #fParent.append(fChild)
                                f.append(fChild)
                    else:
                        continue
            except Exception as e:
                print('elm2etree exception: {}'.format(repr(e)))
                continue
        return elmTree
    except Exception as e:
        print('elm2etree exception: {}'.format(repr(e)))
        return None

def is_element_anypart_in_view(driver, elm):
    try:
        return driver.execute_script('var top = arguments[0].getBoundingClientRect().top; return (top >= 0 && top < window.innerHeight);', elm)
    except Exception as e:
        print('is_element_anypart_in_view exception: {}'.format(repr(e)))
        return False

def element_attributes(driver, elm):
    tag = elm.tag_name
    attrib = driver.execute_script('var items = {}; for (index = 0; index < arguments[0].attributes.length; ++index) { items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value }; return items;', elm)
    for k in attrib:
        if k in custom_attrib:
            attrib.pop(k)
    return attrib

def xpath_from_etree(driver, node):
    tag = node.tag
    attrib = node.attrib
    attribTest = attribute_test(attrib)
    if attribTest is None:
        xpath = '//{}'.format(tag)
    else:
        xpath = '//{}[{}]'.format(tag, attribTest)
    return xpath

def xpath_from_dict(attribDict):
    tag = attribDict.pop('tag')
    attribTest = attribute_test(attribDict)
    if attribTest is None:
        xpath = '//{}'.format(tag)
    else:
        xpath = '//{}[{}]'.format(tag, attribTest)
    return xpath

def parse_words(text):
    separator = r"""!"#$%&'()*+,\-./0123456789:;<=>?@[\\\]\^_`{|}~´·˜∼。"""
    s = re.sub(r'\s+', ' ', re.sub('[\r\n\t]', ' ', re.sub('[{}]'.format(separator), ' ', text))).split(' ')
    return ''.join([x+' ' for x in [x for x in s if (len(x) > 1) or re.search('[^a-zA-Z]', x)]])

def log_message(file, text, printOut=True, driver = None):
    timeStr = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    file.write('{}: {}\n'.format(timeStr, text))
    if printOut:
        print(text)
    if driver is not None:
        fullpage_screenshot(driver, 'error/{}.png'.format(timeStr))

def extract_attributes(root):
    s = []
    for e in root.xpath('descendant-or-self::*'):
        for k in e.attrib:
            if k not in custom_attrib:
                s.append(e.attrib[k])
    return ' '.join(s)
    #return parse_words(s)

def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text()

def mark_element_by_id(driver, ID):
    driver.execute_script(
    """
    elements = get_elements_by_self_id(arguments);
    for (var i = 0; i < elements.length; ++i) 
    {
        try 
        {
            mark_element(elements[i]);
        }
        catch (err) 
        {
            ;
        }
    }
    """, *ID)

def unmark_element_by_id(driver, ID):
    driver.execute_script(
    """
    elements = get_elements_by_self_id(arguments);
    for (var i = 0; i < elements.length; ++i) 
    {
        try 
        {
            unmark_element(elements[i]);
        }
        catch (err) 
        {
            ;
        }
    }
    """, *ID)

def open_new_window(driver):
    try:  
        driver.execute_script('window.open()')
        for i in range(len(driver.window_handles)-1):
            driver.switch_to.window(driver.window_handles[i])
            driver.close()
        driver.switch_to.window(driver.window_handles[-1])
    except Exception:
        pass

def horizon_assemble(elmList):
    """
    Assemble sibling elements using their parent.
    """
    ancestor = [e.xpath('./ancestor::*') for e in elmList]
    ret = []
    while len(elmList) > 0:
        ei = elmList.pop()
        eiAcstr = ancestor.pop()
        comAcstr = ei
        for ej, ejAcstr in zip(elmList.copy(), ancestor.copy()):
            if [a.tag for a in eiAcstr] == [a.tag for a in ejAcstr]:
                for k in range(len(eiAcstr)):
                    if eiAcstr[k] != ejAcstr[k]:
                        break
                if k-1 > 5:
                    elmList.remove(ej)
                    ancestor.remove(ejAcstr)
                    if eiAcstr[k-1] in comAcstr.xpath('./ancestor::*'):
                        comAcstr = eiAcstr[k-1]
        if comAcstr not in ret:
            ret.append(comAcstr)
    return ret

def horizon_assemble_backup(elmList):
    """
    Assemble sibling elements using their parent.
    """
    ret = []
    while len(elmList) > 0:
        ei = elmList.pop()
        hit = False
        if len(ei.xpath('./ancestor::*')) > 5:
            for ej in elmList.copy():
                if ei in ej.xpath('./following-sibling::*|./preceding-sibling::*'):
                    elmList.remove(ej)
                    hit = True
        if hit:
            ret.append(ei.getparent())
        else:
            ret.append(ei)
    return ret

def vertical_assemble(elmList):
    """
    Assemble sibling elements using their parent.
    """
    ancestor = [e.xpath('./ancestor::*') for e in elmList]
    rmIdx = []
    for e in elmList:
        for idx, a in enumerate(ancestor):
            if e in a:
                rmIdx.append(idx)
    ret = [elmList[i] for i in range(len(elmList)) if i not in rmIdx]
    return ret

class ObjXPATH:
    def __init__(self, cursor, *args, **kwargs):
        self.commentButtonXPath = {}
        self.commentContainerXPath = {}
        cursor.execute('SELECT website, comment_button, comment_container FROM object_xpath')
        for r in cursor.fetchall():
            self.commentButtonXPath[r[0]] = r[1]
            self.commentContainerXPath[r[0]] = r[2]
        return super().__init__(*args, **kwargs)