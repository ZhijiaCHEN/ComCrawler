import json
from typing import Dict, List, Tuple, Set
from lxml import html, etree
from json.decoder import JSONDecodeError
import lxml
import matplotlib.pyplot as plt
import os
from types import SimpleNamespace
from collections import defaultdict, deque

ELEMENT_BLACK_LIST = ['script', 'noscript', 'head', 'meta', 'style']
ATTRIB_BLACK_LIST = ['comment_boundary']
def build_lxml_tree(input):
    if hasattr(input, 'read'):
        input = input.read()
    try:
        # if the input is json type, we will convert the json into an etree
        def json_build(parent, jsonNode):
            if type(jsonNode) == dict:
                child = html.Element('dict')
                for key, val in jsonNode.items():
                    grandChild = html.Element(key)
                    child.append(grandChild)
                    if type(val) == str:
                        grandChild.text = val
                    else:
                        json_build(grandChild, val)
            elif type(jsonNode) == list:
                child = html.Element('list')
                for n in jsonNode:
                    json_build(child, n)
            else:
                child = html.Element('null')
                child.text = str(jsonNode)
            parent.append(child)

        input = json.loads(input)
        root = html.Element('json')
        json_build(root, input)
    except JSONDecodeError as e:
        # otherwise, we simply build an etree from the HTML/XML source
        root = etree.HTML(input)
    return root

class StructNode:
    def __init__(self, elm, depth, parent: 'StructNode', root: 'StructTree') -> None:
        self.elm = elm
        self.attrib = elm.attrib
        self.parent = parent
        self.root = root
        self.nodeSignature = (elm.tag, tuple(sorted([k for k in elm.keys() if k not in ATTRIB_BLACK_LIST])))
        self.nodeID: int = None
        self.structSignature = None
        self.structID: int = None
        self.size = 1
        self.height = 1
        self.depth = depth
        self.attribCnt = 0
        self.children = []
        self.startIndex = len(root.nodeSequence)
        for childElement in elm:
            #if type(childElement) != html.HtmlElement or childElement.tag in TAG_BLACK_LIST:
            if type(childElement) == html.HtmlComment or childElement.tag in ELEMENT_BLACK_LIST:
                continue
            childStructNode = StructNode(childElement, depth + 1, self, root)
            self.children.append(childStructNode)
            self.size += childStructNode.size
            self.height = max(self.height, childStructNode.height + 1)
            self.attribCnt += childStructNode.attribCnt
        self.attribCnt += len([a for a in elm.attrib if a not in ATTRIB_BLACK_LIST])
        self.index = len(root.nodeSequence)
        root.nodeSequence.append(self)
        self.endIndex = self.index + 1

        elm.attrib['data-height'] = str(self.height)
        elm.attrib['data-size'] = str(self.size)
        elm.attrib['data-index'] = str(self.index)
        elm.attrib['data-depth'] = str(self.depth)

class StructTree(StructNode):
    def __init__(self, elm) -> None:
        self.node2ID: Dict[tuple, int] = {} # node signature -> node
        self.struct2ID: Dict[tuple, int] = {} # structure signature -> structure ID
        self.structIndex: Dict[int, List[int]] = {} # structure ID -> list of indexes of the structure
        self.structFreqency: Dict[int, int] = {} # structure frequency
        self.structSize: Dict[int, int] = {} # structure ID -> size of the structure
        self.structHeight: Dict[int, int] = {} # structure ID -> height of the structure
        self.nodeSequence: List[StructNode] = []
        super().__init__(elm, 0, None, self)
        self._assign_ID()

    def __getitem__(self, i) -> StructNode:
        return self.nodeSequence[i]

    def _assign_ID(self):
        """Assign node ID and structure ID for each node
        """
        def dfs(node: StructNode):
            structSignature = []
            for child in node.children:
                dfs(child)
                structSignature.append(child.structID)
            node.nodeID = self.node2ID.setdefault(node.nodeSignature, len(self.node2ID) + 1) # node ID starts from 1
            structSignature.append(node.nodeID)
            node.structSignature = tuple(structSignature)
            node.structID = self.struct2ID.setdefault(node.structSignature, len(self.struct2ID) + 1) # structure ID starts from 1
            self.structIndex.setdefault(node.structID, []).append(node.index)
            self.structFreqency[node.structID] = self.structFreqency.setdefault(node.structID, 0) + 1
            self.structSize[node.structID] = node.size
            self.structHeight[node.structID] = node.height
        dfs(self)

    def record_boundary(self, kernelHeightThresh: int, kernelSizeThresh: int, freqThresh: int, recordHeightThresh, recordSizeThresh):
        assert freqThresh >= 3
        freqStruct = set([sid for (sid, cnt) in self.structFreqency.items() if cnt >= freqThresh and self.structHeight[sid] >= kernelHeightThresh and self.structSize[sid] >= kernelSizeThresh])

        # if kernel k1 is a subtree of kernel k2, we will remove k2
        for sid in freqStruct.copy():
            node = self[self.structIndex[sid][0]]
            while node.parent:
                node = node.parent
                if node.structID in freqStruct:
                    freqStruct.remove(node.structID)

        recordRegion = {}
        for sid in freqStruct:
            recordAccumulator = {i: {(sid, ): set([i])} for i in self.structIndex[sid]} # i: index -> p: path -> j: element index, where j is the record expanded from the kernel of index i
            kernelAccumulator = {i: {(sid, ): set([i])} for i in self.structIndex[sid]} # kernels under element of index i
            kernelCounter = {i: [i] for i in self.structIndex[sid]}
            directRecordAccumulator = {i: {(sid, ): set()} for i in self.structIndex[sid]} # records that are index i's children
            root = None
            
            kernelExpansionIndexes = {}
            for kernelIdx in self.structIndex[sid]:
            #for kernelIdx in sorted(self.structIndex[sid], key=lambda i: self[i].depth, reverse=True):
                record = self[kernelIdx]
                nodePath = [sid]
                indexPath = [kernelIdx]
                expand = True
                while record.parent:
                    parent = record.parent
                    kernelCounter.setdefault(parent.index, []).append(kernelIdx)
                    directRecordAccumulator.setdefault(parent.index, {}).setdefault(tuple(nodePath), set()).add(record.index)
                    kernelAccumulator.setdefault(parent.index, {}).setdefault(tuple(nodePath), set()).add(kernelIdx)
                    for oldPath, indexes in kernelAccumulator[record.index].items():
                        kernelAccumulator[parent.index].setdefault(oldPath, set()).update(indexes)
                    recordAccumulator.setdefault(parent.index, {}).setdefault(tuple(nodePath), set()).add(record.index)
                    for oldPath, indexes in recordAccumulator[record.index].items():
                        recordAccumulator[parent.index].setdefault(oldPath, set()).update(indexes)

                    # if expand and len(directRecordAccumulator[parent.index][tuple(nodePath)]) >= 2 and len(recordAccumulator[parent.index][tuple(nodePath)]) >= freqThresh:
                    #     # stop kernel expansion if we arrive at an element that will merge too many kernels
                    #     pathCandidates.add(tuple(nodePath))
                    #     expand = False
                    
                    if root is None and len(kernelCounter[parent.index]) == len(self.structIndex[sid]):
                        root = parent
                    record = parent
                    nodePath.append(parent.nodeID)
                    indexPath.append(parent.index)

                kernelExpansionIndexes[kernelIdx] = indexPath

            pathCandidates = set()
            for kernelIdx in self.structIndex[sid]:
                record = self[kernelIdx]
                nodePath = [sid]
                while record.parent:
                    parent = record.parent
                    # if parent.elm.tag == 'body':
                    #     print('')
                    if len(directRecordAccumulator[parent.index][tuple(nodePath)]) >= 2 and len(recordAccumulator[parent.index][tuple(nodePath)]) >= freqThresh:
                        # stop kernel expansion if we arrive at an element that will merge too many kernels
                        pathCandidates.add(tuple(nodePath))
                        break
                    record = parent
                    nodePath.append(parent.nodeID)

            # throw away over-running paths
            trie = {}
            for path in sorted(pathCandidates, key=lambda p: len(p)):
                p = trie
                for i in path:
                    p = p.setdefault(i, {})
                    if -1 in p:
                        pathCandidates.remove(path)
                        break
                p[-1] = -1 # mark the end of a path

            def query_records(node: StructNode, path):
                nonlocal recordAccumulator, kernelAccumulator, kernelExpansionIndexes, recordRegion, root
                stop = True
                for child in node.children:
                    # find record region, which is the nearest common ancestor of all the kernels
                    if len(recordAccumulator.get(child.index, {}).get(path, set())) == len(recordAccumulator[node.index][path]):
                        stop = False
                        query_records(child, path)
                if stop:
                    kernel2Record = recordRegion.setdefault(node.index, {})
                    record2Kernel = {}
                    recordTexts = set()
                    for kernelIdx in kernelCounter[node.index]:
                        recordIdx = kernelExpansionIndexes[kernelIdx][:len(path)][-1]
                        if recordIdx in recordAccumulator[node.index][path]:
                            record2Kernel.setdefault(recordIdx, [])
                            # recordTextLen.add(self[recordIdx].elm.text_content().replace('/n', ''))
                            recordTexts.add(''.join(self[recordIdx].elm.xpath(".//text()")).replace(' ', '').replace('\n', ''))
                    if len(recordTexts) > len(record2Kernel)//2:
                        for kernelIdx in kernelCounter[node.index]:
                            recordIdx = kernelExpansionIndexes[kernelIdx][:len(path)][-1]
                            if recordIdx in recordAccumulator[node.index][path]:
                                kernel2Record[kernelIdx] = recordIdx
                                record2Kernel.setdefault(recordIdx, []).append(kernelIdx)

            for path in pathCandidates:
                query_records(root, path)
        for k, v in list(recordRegion.items()):
            if len(v) == 0:
                recordRegion.pop(k)
        return recordRegion

    def structure_sequence(self, heightThresh: int, sizeThresh: int) -> List[int]:
        return [(i, node.structID) for (i, node) in enumerate (self.nodeSequence) if node.height >= heightThresh and node.size >= sizeThresh]
