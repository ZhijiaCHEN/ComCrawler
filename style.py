from textdistance import strcmp95
from lxml import etree
from io import StringIO
from utility import *
import psycopg2
from types import SimpleNamespace
from selenium import webdriver
from univeral_tree import StructTree

class MyElement(etree.ElementBase):
    position = None
    
class MyParser(etree.HTMLParser):
    def __init__(self) -> None:
        parser_lookup = etree.ElementDefaultClassLookup(element=MyElement)
        super().__init__(remove_blank_text=True, remove_comments = True)
        self.set_element_class_lookup(parser_lookup)

class AttributeNode:
    # an AttributeNode contains all the tree nodes of the same tag, height and attribute keys
    def __init__(self, tag, attribKeys, attribValues):
        self.attribKeys = attribKeys
        self.attribValues = attribValues
        self.tag = tag
        self.position = {} # hop id: attribute value tuple, previous, next

    def similarity(self, comparedNode):
        """
        Compare this node with another style info node based on the similarity of their outerHTML.
        """
        return sum([strcmp95.normalized_similarity(self.attribValues[i], comparedNode.attribValues[i])/len(self.attribValues) for i in range(len(self.attribValues))])

    @property
    def count(self):
        return len(self.position)

class AttributeNodePosition:
    def __init__(self, attributeNode, index, attributeValues, treeNode, prevNode = None, nextNode = None, startStyle = True, endStyle = False):
        self.node = attributeNode
        self.index = index
        self.attributeValues = attributeValues
        self.prevNode = prevNode
        if prevNode:
            self.prevPositionNode = prevNode.position[index-1]
        else:
            self.prevPositionNode = None
        self.nextNode = nextNode
        if nextNode:
            self.nextPositionNode = nextNode.position[index+1]
        else:
            self.nextPositionNode = None
        self.startStyle = startStyle
        self.endStyle = endStyle
        self.treeNode = treeNode
        self.treeNode.position = self
        self.match = [self]
        

    def __getitem__(self, key):
        assert type(key) == int, 'Subscriptor must be integer.'
        ret = self.node 
        if key >= 0:
            for index in range(self.index, self.index+key):
                ret = ret.position[index].nextNode
                assert ret is not None, 'IndexError: list index out of range'
        else:
            for index in range(self.index, self.index+key, -1):
                ret = ret.position[index].prevNode
                assert ret is not None, 'IndexError: list index out of range'
        return ret

class StyleDict:
    def __init__(self, htmlEtree):
        for node in htmlEtree.xpath('//*'):
            if node.tag in NON_VISUAL_TAGS:
                node.getparent().remove(node)

        def assign_height(node):
            if len(node) > 0:
                heights = [int(n.attrib['data-height']) for n in node]
                node.attrib['data-height'] = str(max(heights) + 1)
            else:
                node.attrib['data-height'] = '0'
        post_order_traversal(htmlEtree.getroot(), assign_height)

        prevNode = None
        self.headNode = None
        self.tailNode = None
        visitCnt = 0
        def first_visit_node(node):
            if node.tag in NON_VISUAL_TAGS:
                return
            nonlocal visitCnt
            nonlocal prevNode
            attribKeys = tuple(sorted([k for k in node.attrib if k not in custom_attrib]))
            attribValues = tuple(node.attrib[k] for k in attribKeys)
            thisAttribeNode = self._add_node(node.tag, int(node.attrib[NODE_HEIGHT]), attribKeys, attribValues, visitCnt, node)
            thisPosition = thisAttribeNode.position[visitCnt]
            thisPosition.prevNode = prevNode
            if prevNode is not None:
                prevPosition = prevNode.position[visitCnt-1]
                prevPosition.nextNode = thisAttribeNode
                prevPosition.nextPositionNode = thisPosition
                thisPosition.prevPositionNode = prevPosition
            else:
                self.headNode = thisAttribeNode
            prevNode = thisAttribeNode
            self.tailNode = thisAttribeNode

            thisPosition.startStyle = True
            thisPosition.endStyle = False
            visitCnt += 1
        
        def second_visit_node(node):
            nonlocal visitCnt
            nonlocal prevNode
            attribKeys = tuple(sorted([k for k in node.attrib if k not in custom_attrib]))
            attribValues = tuple(node.attrib[k] for k in attribKeys)
            thisAttribeNode = self._add_node(node.tag,int(node.attrib[NODE_HEIGHT]), attribKeys, attribValues, visitCnt, node)
            thisPosition = thisAttribeNode.position[visitCnt]
            thisPosition.prevNode = prevNode

            prevPosition = prevNode.position[visitCnt-1]
            prevPosition.nextNode = thisAttribeNode
            prevPosition.nextPositionNode = thisPosition
            thisPosition.prevPositionNode = prevPosition

            prevNode = thisAttribeNode
            self.tailNode = thisAttribeNode

            thisPosition.startStyle = False
            thisPosition.endStyle = True
            visitCnt += 1

        self._styleDict = {}
        thisNode = htmlEtree.getroot()
        #double_traversal(thisNode, first_visit_node, second_visit_node)
        post_order_traversal(thisNode, first_visit_node)

        self.etree = htmlEtree

        self._match_node(0.8)

    def _add_node(self, tag, height, attribKeys, attribValues, cnt, treeNode):
        styleKey = (tag, height) + attribKeys
        if styleKey in self._styleDict:
            node = self._styleDict[styleKey]
        else:
            node = AttributeNode(tag, attribKeys, attribValues)
            self._styleDict[styleKey] = node
        node.position[cnt] = AttributeNodePosition(node, cnt, attribValues, treeNode, prevNode = None, nextNode = None)
        return node

    def _match_node(self, strSimThresh):
        for k in sorted(list(self.keys()), key=lambda x:x[1]):
            sNode = self[k]
            position = [p for p in sNode.position if TOUCHED not in sNode.position[p].treeNode.attrib]
            while len(position) > 0:
                s1 = sNode.position[position.pop()]
                for s2Position in [p for p in position]:
                    s2 = sNode.position[s2Position]
                    sim = tuple_similarity(s1.attributeValues, s2.attributeValues)
                    if  sim >= strSimThresh and len(s1.treeNode) == len(s2.treeNode):
                        match = True
                        for child1, child2 in zip(s1.treeNode, s2.treeNode):
                            if child1.position.match != child2.position.match:
                                match = False
                                break
                        if match:
                            s1.match.append(s2)
                            s2.match = s1.match
                            position.remove(s2Position)
    
    def look_up_node(self, node):
        pass
    
    def __getitem__(self, key):
        return self._styleDict[key]

    def __iter__(self):
        return self._styleDict.__iter__()
    
    def keys(self):
        return self._styleDict.keys()

def structured_blocks(driver):
    try:
        javascript_init(driver)
        driver.execute_script('assign_myid();')
        pageHTML = '<html>{}</html>'.format(driver.execute_script('return document.body.outerHTML'))
        pageEtree = etree.parse(StringIO(pageHTML), MyParser())
        ## get iframe contents
        iframeTreeElms = [f for f in pageEtree.xpath('//iframe')]
        for frmTreeElm in iframeTreeElms:
            if SELF_ID in frmTreeElm.attrib:
                try:
                    frmDOMelm = driver.find_element_by_xpath('//iframe[@{}="{}"]'.format(SELF_ID, frmTreeElm.attrib[SELF_ID]))
                except Exception as e:
                    frmDOMelm = None
            else:
                frmTreeElm.getparent().remove(frmTreeElm)
                continue
            if frmDOMelm is None: continue
            try:
                driver.switch_to.frame(frmDOMelm)
                frmHTML = '<html>{}</html>'.format(driver.execute_script('return document.body.outerHTML'))
                frmTreeElm.append(etree.parse(StringIO(frmHTML), MyParser()).getroot())
                driver.switch_to.default_content()
            except Exception as e:
                print(repr(e))
                frmTreeElm.getparent().remove(frmTreeElm)
                driver.switch_to.default_content()
    except Exception as e:
        print('structured_blocks: {}'.format(repr(e)))
        return ([], [])

    sTree = StructTree(pageEtree.getroot())
    regionDict = sTree.record_boundary(3, 5, 3, 5, 7)
    recordRegion = [sTree[regionIdx].elm for regionIdx in regionDict]
    
    structDomElm = []
    structEtreeElmRet = []
    for eElm in recordRegion:
        if SELF_ID in eElm.attrib:
            try:
                dDlm = driver.find_element_by_xpath('//*[@{}="{}"]'.format(SELF_ID, eElm.attrib[SELF_ID]))
            except Exception as e:
                dDlm = None
            if dDlm is not None:
                structDomElm.append(dDlm)
                structEtreeElmRet.append(eElm)
        else:
            # this may be an element inside an iframe that id is not assigned
            frm = eElm.xpath('./ancestor-or-self::iframe')
            if len(frm) > 0 and SELF_ID in frm[0].attrib:
                frm = frm[0]
                try:
                    dElm = driver.find_element_by_xpath('//iframe[@{}="{}"]'.format(SELF_ID, frm.attrib[SELF_ID]))
                    if dElm is not None and dElm not in structDomElm:
                        structDomElm.append(dElm)
                        structEtreeElmRet.append(eElm)
                except Exception as e:
                    pass
    return (structEtreeElmRet, structDomElm)

if __name__ == "__main__":
    driver = webdriver.Firefox()
    #open_page(driver, 'https://www.nytimes.com/2020/02/12/us/politics/justice-department-roger-stone-sentencing.html#commentsContainer')
    open_page(driver, 'https://www.phonearena.com/news/Galaxy-Z-Flip-sells-out-in-7.5-hours-in-South-Korea_id122246')
    #open_page(driver, 'https://www.calciomercato.com/news/juve-alex-sandro-dobbiamo-segnare-di-piu-de-ligt-deve-stare-tran-31491')
    driver.execute_script('assign_myid()')
    
    
    tree = etree.parse(StringIO('<html>{}</html>'.format(driver.execute_script('return document.body.outerHTML;'))), MyParser())
    styleDict = StyleDict(tree)
    ids = []
    def tmp(node):
        if int(node.attrib[NODE_HEIGHT]) > 3 and len(node.position.match) > 5 and len(node.getparent().position.match) == 1:
            if SELF_ID in node.attrib:
                ids.append(node.attrib[SELF_ID])
    post_order_traversal(tree.getroot(), tmp)
    driver.execute_script(
    """
    elements = get_elements_by_self_id(arguments);
    for (var i = 0; i < elements.length; ++i) 
    {
        try 
        {
            elements[i].style.border = "red solid";
        }
        catch (err) 
        {
            ;
        }
    }
    """, *ids)
    