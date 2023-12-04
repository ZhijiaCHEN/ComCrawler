window.myRoot = document.evaluate('//body[1]', document, null, XPathResult.UNORDERED_NODE_ITERATOR_TYPE, null).iterateNext();
window.traversalOrder = 0;
window.elementSections = [];
window.isNewPage = false;
window.innerHeight = window.innerHeight;
function assign_myid_recursion(node, parentID, depth) {
    if (node.tagName == 'SCRIPT' || node.tagName == 'NOSCRIPT') {
        return;
    }
    var selfID;
    if (node.hasAttribute('data-self-id')) {
        selfID = node.getAttribute('data-self-id');
    }
    else {
        window.traversalOrder += 1;
        selfID = window.traversalOrder;
        node.setAttribute('data-self-id', selfID);
        node.setAttribute('data-parent-id', parentID);
        node.setAttribute('data-depth', depth);
    }

    var children = document.evaluate('./child::*', node, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
    for (var i = 0; i < children.snapshotLength; i++) {
        child = children.snapshotItem(i);
        assign_myid_recursion(child, selfID, depth + 1);
    }
}
window.assign_myid_recursion = assign_myid_recursion;

function assign_myid() {
    window.elementSections.push(window.traversalOrder);
    assign_myid_recursion(window.myRoot, window.traversalOrder, 0);
}
window.assign_myid = assign_myid;

function assign_z_index(zIndex) {
    var rslt = document.evaluate('./ancestor-or-self::*', arguments[0], null, XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
    for (var i = 0; i < rslt.snapshotLength; i++) {
        rslt.snapshotItem(i).style.zIndex = arguments[1];
    }
}
window.assign_z_index = assign_z_index;

function get_elements_by_xpath(xpath, refNode) {
    ret = [];
    result = document.evaluate(xpath, refNode, null, XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
    for (var i = 0; i < result.snapshotLength; i++) {
        ret.push(result.snapshotItem(i))
    }
    return ret;
}
window.get_elements_by_xpath = get_elements_by_xpath;

function get_element_by_xpath(xpath, refNode) {
    return document.evaluate(xpath, refNode, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
}
window.get_element_by_xpath = get_element_by_xpath;

function get_elements_by_self_id(idArray) {
    ret = [];
    for (var i = 0; i < idArray.length; ++i) {

        try {
            var elm = document.evaluate('//*[@data-self-id="' + idArray[i] + '"]', document, null, XPathResult.ANY_UNORDERED_NODE_TYPE, null).singleNodeValue;
            ret.push(elm);
        }
        catch (err) {
            ret.push(null);
        }
    }
    return ret;
}
window.get_elements_by_self_id = get_elements_by_self_id;

function get_elements_by_tag(tag) {
    ret = [];
    var rslt = document.evaluate('.//' + tag, document, null, XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
    for (var i = 0; i < rslt.snapshotLength; i++) {
        ret.push(rslt.snapshotItem(i));
    }
    return ret;
}
window.get_elements_by_tag = get_elements_by_tag;

function get_newly_loaded_elements() {
    //returns the outer most elements that are newly loaded by checking if an element's self-id is greater than the last traversalOrder
    startId = elementSections[elementSections.length - 1];
    ret = [];
    function traversal(node) {
        if (parseInt(node.getAttribute('data-self-id')) >= startId) {
            ret.push(node);
            //also extract content of iframes if exists
            var iframes = document.evaluate('.//iframe', node, null, XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
            for (var i = 0; i < iframes.snapshotLength; i++) {
                ret.push(iframes.snapshotItem(i))
            }

            return;
        }
        else {
            var children = document.evaluate('./child::*', node, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
            for (var i = 0; i < children.snapshotLength; i++) {
                child = children.snapshotItem(i);
                traversal(child);
            }
        }

    }
    traversal(myRoot);
    return ret;
}
window.get_newly_loaded_elements = get_newly_loaded_elements;

function mark_element(elm) {
    try {
        
        elm.style.border = "red solid";
        window.tmpElmBkgnd = elm.style.backgroundColor;
        elm.style.backgroundColor="#FDFF47";
    }
    catch (err) {
        console.log(err);
    }
}
window.mark_element = mark_element;

function unmark_element(elm) {
    try {
        
        elm.style.border = "";
        elm.style.backgroundColor=window.tmpElmBkgnd;
    }
    catch (err) {
        console.log(err);
    }
}
window.unmark_element = unmark_element;

function extract_outer_html(elms) {
    ret = []
    for (var i = 0; i < elms.length; ++i) {
        try {
            if (elms[i].tagName == 'IFRAME') {
                ret.push(elms[i].contentWindow.document.body.outerHTML);
            }
            else {
                ret.push(elms[i].outerHTML);
            }
        }
        catch (err) {
            ret.push('<error>' + err + '</error>')
        }
    }
    return ret;
}
window.extract_outer_html = extract_outer_html;

function editDistance(s1, s2) {
    s1 = s1.toLowerCase();
    s2 = s2.toLowerCase();

    var costs = new Array();
    for (var i = 0; i <= s1.length; i++) {
        var lastValue = i;
        for (var j = 0; j <= s2.length; j++) {
            if (i == 0)
                costs[j] = j;
            else {
                if (j > 0) {
                    var newValue = costs[j - 1];
                    if (s1.charAt(i - 1) != s2.charAt(j - 1))
                        newValue = Math.min(Math.min(newValue, lastValue),
                            costs[j]) + 1;
                    costs[j - 1] = lastValue;
                    lastValue = newValue;
                }
            }
        }
        if (i > 0)
            costs[s2.length] = lastValue;
    }
    return costs[s2.length];
}

function similarity(s1, s2) {
    var longer = s1;
    var shorter = s2;
    if (s1.length < s2.length) {
        longer = s2;
        shorter = s1;
    }
    var longerLength = longer.length;
    if (longerLength == 0) {
        return 1.0;
    }
    return (longerLength - editDistance(longer, shorter)) / parseFloat(longerLength);
}

function find_article_element() {
    var pNode = [];
    var pNodeTextLen = [];
    var pNodeCluster = [];
    var iterator = document.evaluate('//p[not(*) and string-length(text()) > 0]|//div[not(*) and string-length(text()) > 0]', document, null, XPathResult.UNORDERED_NODE_ITERATOR_TYPE, null);
    var thisElement = iterator.iterateNext();
    while (thisElement) {
        pNode.push(thisElement);
        pNodeTextLen.push(thisElement.textContent.length);
        pNodeCluster.push([thisElement])
        thisElement = iterator.iterateNext();
    }

    function cluster_main_content(elmArray) {
        /*
        This function iterates over the given elmArray and merge two nodes if the one of the following condition is true:
        1. One node is descendant of the other.
        2. Starting from their nearest common ancestor node, they have the same distance to the ancestor node, and the corresponding nodes in their paths to the ancestor node have the same style.
        */
        console.log('number of elmement to cluster: '+elmArray.length);
        var clusterMark = Array(elmArray.length).fill(false)
        var clusterArray = [];
        for (var i = 0; i < elmArray.length; ++i) {
            if (clusterMark[i]) {
                continue;
            }
            console.log('cluster for the ' + i + 'th element: \n'+elmArray[i].outerHTML);
            clusterMark[i] = true;  
            var cluster = [elmArray[i]];
            clusterArray.push(cluster);
            for (var j = i+1; j < elmArray.length; ++j) {
                if (clusterMark[j]) {
                    continue;
                }
                var parent = elmArray[i].parentElement;
                while (parent) {
                    if (parent.contains(elmArray[j])) {
                        //check
                        var p1 = elmArray[i];
                        var p2 = elmArray[j];
                        var match = true;
                        var attrib1 = '';
                        var attrib2 = '';
                        while (p1 && p2 && (p1 != parent) && (p2 != parent) && (p1.tagName == p2.tagName) && (p1.attributes.length == p2.attributes.length)) {
                            var attribVal1 = '';
                            var attribVal2 = '';
                            for (var k = 0; k < p1.attributes.length; k++) {
                                if ((p1.attributes[k].name != p2.attributes[k].name)) {
                                    match = false;
                                    break;
                                }
                                else
                                {
                                    attribVal1 += p1.attributes[k].value;
                                    attribVal2 += p2.attributes[k].value;
                                    attrib1 += p1.attributes[k].name + ': ' + p1.attributes[k].value + '\n;';
                                    attrib2 += p2.attributes[k].name + ': ' + p2.attributes[k].value + '\n;';
                                }
                            }
                            var sim = similarity(attribVal1, attrib2);
                            if (sim < 0.85)
                            {
                                match = false;
                            }
                            if (!match) {
                                break;
                            }
                            allert('attribute match with ' + sim + ' similarity : \n' + '\t' + attribVal1 + '\n\t'+attribVal2);
                            p1 = p1.parentElement;
                            p2 = p2.parentElement;
                        }
                        if (match) {
                            
                            console.log('sibling with the ' + j + 'th element: \n'+elmArray[j].outerHTML);
                            cluster.push(elmArray[j]);
                            clusterMark[j] = true;
                        }
                        break;
                    }
                    parent = parent.parentElement;
                }
            }
        }
        return clusterArray;
    }

    function paragraph_text_length(elm) {
        var ret = 0;
        var pChildren = document.evaluate('.//p|.//div', elm, null, XPathResult.UNORDERED_NODE_ITERATOR_TYPE, null);
        var p = pChildren.iterateNext();
        while (p) {
            ret += p.textContent.length;
            p = pChildren.iterateNext();
        }
        return ret;
    }

    var candidates = cluster_main_content(pNode).sort(function (a, b) {
        var la = 0;
        var lb = 0;
        a.forEach(function(item, index)
        {
            la += paragraph_text_length(item);
        });
        b.forEach(function(item, index)
        {
            lb += paragraph_text_length(item);
        });
        return lb - la;
    });

    if (candidates.length > 0) {
        candidates[0].forEach(function(item, index)
        {
            item.style.border = "red dotted";
        });
        candidates[0][0].parentElement.style.border = "red solid";
        for (var i = 1; i < candidates.length; ++i) {
            candidates[i].forEach(function(item, index)
            {
                item.style.border = "black dotted";
            });
            candidates[i][0].parentElement.style.border = "black solid";
            }
    }

    /*
    var idxSort = [...Array(candidates.length).keys()].sort(function(a, b)
    {
        //return pNum[b]-pNum[a] || paragraph_text_length(candidates[b])-paragraph_text_length(candidates[a]);
        return paragraph_text_length(candidates[b])-paragraph_text_length(candidates[a]);
    });
    var s = candidates[idxSort[0]];
    var mergeFlag = true;
    while (mergeFlag)
    {
        mergeFlag = false;
        idxSort.forEach(function (item, index) 
        {
            if (s.parentElement && candidates[item].parentElement)
            {
                if (s.parentElement == candidates[item].parentElement)
                {
                    s = s.parentElement;
                    mergeFlag = true;
                }
            }            
        });
    }
    s.style.border = "red solid";
    */
}
window.find_article_element = find_article_element;

function record_position()
{
    document.body.setAttribute("data-position", `{'x': 0, 'y':0, 'width': ${document.body.scrollWidth}, 'height': ${document.body.scrollHeight}}`);
    var iterator = document.evaluate('//a|//button', document, null, XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
    for (var i = 0; i < iterator.snapshotLength; i++) 
    {
        thisElement = iterator.snapshotItem(i);
        try
        {
            rect = thisElement.getBoundingClientRect();
            thisElement.setAttribute("data-position", `{'x': ${rect.x}, 'y':${rect.y}, 'width': ${rect.width}, 'height': ${rect.height}}`);
        }
        catch(error)
        {
            ;
        }

    }
}
window.record_position = record_position;

function touch_elements()
{
    window.touched = true;
    var thisElement = document.body;
    do
    {
        thisElement.setAttribute('data-touched', '1');
        thisElement.isTrivial = is_element_trivial(thisElement);
        //var rect = thisElement.getBoundingClientRect();
        //thisElement.myHeight = rect.height;
        //thisElement.myWidth = rect.width;
        if (thisElement.firstElementChild == null)
        {
            while((thisElement.nextElementSibling == null)&&(thisElement != document.body))
            {
                thisElement = thisElement.parentElement;
            }
            if (thisElement != document.body)
            {
                thisElement = thisElement.nextElementSibling;
            }
        }
        else
        {
            thisElement = thisElement.firstElementChild;
        }
    }
    while((thisElement != null) && (thisElement != document.body))
}
window.touch_elements = touch_elements;

function feedbacks_new_elements()
{
    var ret = [];
    var thisElement = document.body;
    if (thisElement)
    {
        do
        {
            var touched = thisElement.hasAttribute('data-touched');
            if (!touched)
            {
                ret.push(thisElement);
            }
            if (!touched || (thisElement.firstElementChild == null))
            {
                while((thisElement.nextElementSibling == null)&&(thisElement != document.body))
                {
                    thisElement = thisElement.parentElement;
                }
                if (thisElement != document.body)
                {
                    thisElement = thisElement.nextElementSibling;
                }
            }
            else
            {
                thisElement = thisElement.firstElementChild;
            }
        }
        while((thisElement != null) && (thisElement != document.body))
    }
    return ret;
}
window.feedbacks_new_elements = feedbacks_new_elements;

function feedbacks_new_element_text()
{
    var untouched = feedbacks_new_elements();
    var ret = '';
    for(var i =0; i < untouched.length; ++i)
    {
        ret += ('\t'+untouched[i].outerHTML);
    }
    return ret;
}
window.feedbacks_new_element_text = feedbacks_new_element_text;

function feedbacks_new_size()
{
    var ret = [];
    var thisElement = document.body;
    function is_feedback(element)
    {   /*
        if (!in_view(element))
        {
            return false;
        }
        */
        if (element == document.body)
        {
            return false;
        }
        if (!is_element_trivial(element))
        {   
            if (thisElement.hasAttribute('data-touched'))
            {
                //var rect = element.getBoundingClientRect();
                if(element.isTrivial && !is_element_trivial(element))
                {
                    //console.log('get size changed element: '+thisElement.outerHTML);
                    return true;
                }
                else
                {
                    return false;
                }
            }
            else
            {
                return true;  
            }
        }
        else
        {
            return false;
        }
    }
    if (thisElement)
    {
        do
        {
            /*
            if (thisElement.hasAttribute('data-self-id'))
            {
                console.log('check feedback for id: '+thisElement.getAttribute('data-self-id'));
            }
                
            thisElement.setAttribute('data-feedback-touched', 'true');
            */
            var isFeedback = is_feedback(thisElement);
            
            if (thisElement != document.body && isFeedback)
            {
                ret.push(thisElement);
                /*
                var iframes = document.evaluate('.//iframe', thisElement, null, XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
                for (var i = 0; i < iframes.snapshotLength; i++) 
                {
                    if(!is_element_trivial(iframes.snapshotItem(i)))
                    {
                        ret.push(iframes.snapshotItem(i));
                    }
                }
                */
            }
            if (isFeedback || (thisElement.firstElementChild == null))
            {
                while((thisElement.nextElementSibling == null)&&(thisElement != document.body))
                {
                    thisElement = thisElement.parentElement;
                }
                if (thisElement != document.body)
                {
                    thisElement = thisElement.nextElementSibling;
                }
            }
            else
            {
                thisElement = thisElement.firstElementChild;
            }
        }
        while((thisElement != null) && (thisElement != document.body))
    }
    
    var whileFlag = true;
    while(whileFlag)
    {
        whileFlag = false;
        for (var i = 0; i < ret.length; ++i)
        {
            if (ret[i] == null) continue;
            for (var j = 0; j < ret.length; ++j)
            {
                if (i == j || ret[j] == null) continue;
                if (ret[i].contains(ret[j]))
                {
                    ret[j] = null;
                    continue;
                }
                if (ret[i].parentElement == ret[j].parentElement && ret[i].parentElement != document.body && ret[i].parentElement.parentElement != document.body && ret[j].parentElement != document.body && ret[j].parentElement.parentElement != document.body)
                {
                    var childreni = document.evaluate('./child::*', ret[i], null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                    var childrenj = document.evaluate('./child::*', ret[j], null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                    if (childreni.snapshotLength == childrenj.snapshotLength)
                    {
                        var match = true;
                        for (var k = 0; k < childreni.snapshotLength; k++) 
                        {
                            childi = childreni.snapshotItem(k);
                            childj = childrenj.snapshotItem(k);
                            if (childi.tagName != childj.tagName)
                            {
                                match = false;
                                break;
                            }
                        }
                        if (match)
                        {
                            ret[i] = ret[i].parentElement;
                            whileFlag = true;
                        }
                    }
                }
            }

        }
    }
    /*
    var tempRet = [];
    for (var i = 0; i < ret.length; ++i)
    {   var elm = ret[i];
        if (elm)
        {
            tempRet.push(elm);
        }
    }
   
    return tempRet;
    */
    return ret;
}
window.feedbacks_new_size = feedbacks_new_size;

function feedbacks_new_size_text()
{
    var untouched = feedbacks_new_size();
    var ret = '';
    for(var i =0; i < untouched.length; ++i)
    {
        ret += ('\t'+untouched[i].outerHTML);
    }
    return ret;
}
window.feedbacks_new_size_text = feedbacks_new_size_text;

/*
this function assgins a click id for each clickable object and returns an array of attributes names and corresponding values for each clickable object.
*/
function assign_click_id()
{
    window.clickables = []
    document.body.setAttribute("data-position", `{'x': 0, 'y':0, 'width': ${document.body.scrollWidth}, 'height': ${document.body.scrollHeight}}`);
    var ret = [];
    var clickObjCnt = 0;
    clickableTags = ['a', 'button']
    for (var k = 0; k < clickableTags.length; ++k)
    {
        result = document.evaluate('.//'+clickableTags[k], document.body, null, XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
        for (var i = 0; i < result.snapshotLength; i++)
        {
            try
            {
                var elem = result.snapshotItem(i);
                var rect = elem.getBoundingClientRect();
                if (rect.width+rect.height == 0)
                {
                    continue
                }
                var attrib = {'tag': clickableTags[k], 'ancestors-tag':[], 'ancestors-idx':[]};
                for (var j = 0; j < elem.attributes.length; j++)
                {
                    if (elem.attributes[j].name == 'href')
                    {
                        attrib[elem.attributes[j].name] = elem.href;//get the complete url
                    }
                    else
                    {
                        attrib[elem.attributes[j].name] = elem.attributes[j].value;
                    }
                }
                var p = elem.parentElement;
                while(p)
                {
                    attrib['ancestors-tag'].push(p.tagName);
                    var ancestorsIdx = 0;
                    var s = p.previousElementSibling;
                    while(s)
                    {
                        ancestorsIdx += 1;
                        s = s.previousElementSibling;
                    }
                    attrib['ancestors-idx'].push(ancestorsIdx);
                    p = p.parentElement;
                }
                clickables.push(elem);
                elem.setAttribute('data-click-id', clickables.length.toString());
                attrib['data-click-id'] = clickables.length;
                elem.setAttribute("data-position", `{'x': ${rect.x}, 'y':${rect.y}, 'width': ${rect.width}, 'height': ${rect.height}}`);
                ret.push(attrib);
                //ret[0].push(attribNames);
                //ret[1].push(attribValues);
            }
            catch (error)
            {
                console.log('assign_click_id: '+error);
            }
        }
    }
    return ret;
}
window.assign_click_id = assign_click_id;

function get_clickable_attributes() {
    window.clickables = []
    var ret = [];
    var clickObjCnt = 0;
    clickableTags = ['a', 'button']
    for (var k = 0; k < clickableTags.length; ++k) {
        result = document.evaluate('.//' + clickableTags[k], document.body, null, XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
        for (var i = 0; i < result.snapshotLength; i++) {
            try {
                var elem = result.snapshotItem(i);
                var rect = elem.getBoundingClientRect();
                if (rect.width + rect.height == 0) {
                    continue
                }
                var attrib = { 'tag': clickableTags[k] };
                var prepend = false;
                for (var j = 0; j < elem.attributes.length; j++) {
                    if (elem.attributes[j].name == 'href') {
                        attrib[elem.attributes[j].name] = elem.href;//get the complete url
                        if (elem.href.substring(0, 4) == 'http')
                        {
                            prepend = true;
                        }
                    }
                    else {
                        attrib[elem.attributes[j].name] = elem.attributes[j].value;
                    }
                }
                if (prepend)
                {
                    clickables.unshift(elem);
                    ret.unshift(attrib);
                }
                else
                {
                    clickables.push(elem);
                    ret.push(attrib);
                }
            }
            catch (error) {
                console.log('get_clickable_attributes: ' + error);
            }
        }
    }
    return ret;
}
window.get_clickable_attributes = get_clickable_attributes;


function clean_dom()
{
    var iterator = document.evaluate('//script|//noscript|//style|//meta', document, null, XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
    for (var i = 0; i < iterator.snapshotLength; i++) 
    {
        thisElement = iterator.snapshotItem(i);
        try
        {
            thisElement.parentElement.removeChild(thisElement);
        }
        catch(error)
        {
            ;
        }

    }
}
window.clean_dom = clean_dom;

var get_url_location = function(href) {
    var l = document.createElement("a");
    l.href = href;
    return l;
};
window.get_url_location = get_url_location

function extract_all_href()
{
    var thisHost = window.location.host;
    var ret = [];
    var iterator = document.evaluate('//a', document, null, XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
    for (var i = 0; i < iterator.snapshotLength; i++) 
    {
        thisElement = iterator.snapshotItem(i);
        try
        {
            var location = new URL(thisElement.href);
            if (location.host == thisHost)
            {
                ret.push(thisElement.href);
            }
        }
        catch(error)
        {
            ;
        }
    }
    return ret;
}
window.extract_all_href = extract_all_href;

function get_following_siblings(elm)
{
    var siblings = [];
    var nSib = elm.nextElementSibling;
    while (nSib) 
    {   
        if(!is_element_trivial(nSib))
        {
            siblings.push(nSib);
        }        
        nSib = nSib.nextElementSibling;
    }
    return siblings;
}
window.get_following_siblings = get_following_siblings;

function is_element_trivial(elm)
{
    var style = window.getComputedStyle(elm, null);
    if (style.getPropertyValue('opacity') < 0.1)
    {
        return true;
    }
    var hThresh = window.innerHeight/100;
    var wThresh = window.innerWidth/100;
    try
    {
        var children = document.evaluate('./descendant-or-self::*', elm, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
        for (var i = 0; i < children.snapshotLength; i++) 
        {
            child = children.snapshotItem(i);
            try
            {
                var rect = child.getBoundingClientRect();
                if((rect.width > hThresh) && (rect.height > wThresh))
                {
                    return false;
                }
                else
                {
                    return true;
                }
            }
            catch(err)
            {
                continue;
            }
            
        }
    }
    catch (err)
    {
        return true;
    }
    return true;
    
}
window.is_element_trivial = is_element_trivial;

function in_view(element)
{
    var rect = element.getBoundingClientRect();
    return (rect.top >= 0) && (rect.top < innerHeight);
}
window.in_view = in_view;

function below_view(element)
{
    var rect = element.getBoundingClientRect();
    return (rect.top > innerHeight);
}
window.below_view = below_view;

function get_elements_in_view()
{
    var ret = [];
    var thisElement = document.body;
    if (thisElement)
    {
        do
        {
            var inView = in_view(thisElement);
            var belowView = below_view(thisElement);
            var top = thisElement.getBoundingClientRect().top; //filter out elements with zero top, which are probably a body or a menu

            if (thisElement != document.body && inView && top > window.innerHeight/100)
            {
                if (!is_element_trivial(thisElement))
                {
                    ret.push(thisElement);
                }
                
                /*
                var iframes = document.evaluate('.//iframe', thisElement, null, XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
                for (var i = 0; i < iframes.snapshotLength; i++) 
                {
                    if(!is_element_trivial(iframes.snapshotItem(i)))
                    {
                        ret.push(iframes.snapshotItem(i));
                    }
                }
                */
            }
            if ((inView&&thisElement != document.body && top > window.innerHeight/100) /*|| belowView*/ || (thisElement.firstElementChild == null)) //condition for stop searching descendants
            {
                while((thisElement.nextElementSibling == null)&&(thisElement != document.body))
                {
                    thisElement = thisElement.parentElement;
                }
                if (thisElement != document.body)
                {
                    thisElement = thisElement.nextElementSibling;
                }
            }
            else
            {
                thisElement = thisElement.firstElementChild;
            }
        }
        while((thisElement != null) && (thisElement != document.body))
    }
    return ret;
}
window.get_elements_in_view = get_elements_in_view;

function element_offset(el) 
{
    var rect = el.getBoundingClientRect(),
    scrollLeft = window.pageXOffset || document.documentElement.scrollLeft,
    scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    return { top: rect.top + scrollTop, left: rect.left + scrollLeft }
}
window.element_offset = element_offset;

function element_scroll_into_view(el)
{
    window.scrollTo(0, element_offset(arguments[0]).top-window.innerHeight/10);
}
window.element_scroll_into_view = element_scroll_into_view;