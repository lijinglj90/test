#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''
    **XmlCfg** 本模块为基于Xml的配置文件操作接口模块，实现对指定配置项的修改和读取接口

    

'''
 
from xml.dom.minidom import parse
import xml.dom.minidom
import os
from xml.dom.minidom import Element
from xml.dom.minidom import Node
import logger as lg
import chardet

class XmlCfg():
    '''xml操作类'''

    #节点串连接符
    __node_splitstr='@@'

    #条件串外层连接符
    __con_filter="@@"
    #条件串外层连接符
    __con_nodefilter="|"

    #条件元串连接符
    __con_innerfilter="@"

    #条件元串并联连接符
    __con_and = "#AND#"
    
    def __init__(self,cfgpath:str): 
        '''构造函数
            功能：
                通过传入参数创建DOM对象
            参数：
                cfgpath，文件的路径，建议为绝对路径
        '''
        self.__cfgpath = cfgpath

        get_encoding = self.get_encoding(self.__cfgpath)
        if get_encoding:  # 程序自动获取文件编码格式，不为空
            self._encoding = get_encoding  # 使用程序获取的编码格式
        else:
            self._encoding = 'utf-8'  # 给一个默认值

        if not os.path.isfile(cfgpath):
            self.__hasfile = False
        else:
            self.__hasfile = True
            self.__domtree = xml.dom.minidom.parse(cfgpath)
            self.__documentElement = self.__domtree.documentElement

    class Filter():
        '''节点选择定位条件结构
            属性说明：
                type：条件对象类型，xml节点为"NodeCoN",xml节点属性为"AttrCon"
                name: 条件对象名，当type为"AttrCon"时，取xml节点属性名，当type为"NodeCoN"时取固定值"_"
                value: 条件对象值
        '''
        def __init__(self,type,name,value):
            self.type = type
            self.name = name
            self.value = value
    
    class Node_Filter():
        '''节点-条件对结构
            属性说明：
                type：条件对象类型，xml节点为"NodeCoN",xml节点属性为"AttrCon"
                name: 条件对象名，当type为"AttrCon"时，取xml节点属性名，当type为"NodeCoN"时取固定值"_"
                value: 条件对象值
        '''

        def __init__(self,node):
            self.node = node
            self.filters = []
        
        
        def addfilter(self,type,name,value):
            '''添加条件到队列
                参数参见Filter属性
            '''
            _filter  = XmlCfg.Filter(type,name,value)
            self.filters.append(_filter)

    
    def __compilecon__(self,con_str:str):
        '''条件处理
            把条件字符串分拆成条件对
            参数：
                条件字符串，格式举例：Node1_Name|AttrCon@Attr_Name@value#AND#NodeCoN@_@value@@Node2_Name|AttrCon@Attr_Name@value#AND#NodeCoN@_@value
            返回：
                条件映射：如正确解析，返回条件映射。当异常时为None，当条件串为空时为None
        '''
        dict_nodeflt = {}
        if con_str == "":
            info = ">> 条件为空[%s]" % con_str
            lg.myloger.error(info)
            return dict_nodeflt,info

        nodeftrs = con_str.split(self.__con_filter)
        for nodeftr in nodeftrs:
            ftrpair = nodeftr.split(self.__con_nodefilter)
            if len(ftrpair) != 2:
                info = ">> 条件[%s]格式错误：在[%s]处" % (con_str,nodeftr)
                lg.myloger.error(info)
                return None,info
            nodeflr_obj = XmlCfg.Node_Filter(ftrpair[0])
            fltstr = ftrpair[1]
            flts = fltstr.split(self.__con_and)
            for flt in flts:
                items = flt.split(self.__con_innerfilter)
                if len(items) != 3 or (items[0] != "AttrCon" and items[0] != "NodeCon"):
                    info = ">> 条件[%s]格式错误：在[%s]处" % (con_str,flt)
                    lg.myloger.error(info)
                    return None,info
                nodeflr_obj.addfilter(items[0], items[1], items[2])

            dict_nodeflt[ftrpair[0]] = nodeflr_obj

        return dict_nodeflt,""


    def __getnode(self, nodes:list, filters:list):
        ''' 根据过滤条件从节点列表获取正确节点
            传入参数：
                nodes：备选节点列表
                filters：选择条件集合
            返回：
                如果有唯一匹配节点，则返回匹配节点，否则返回None
        '''
        tarNodes = []
        for el in nodes:
            finded = False
            if filters is None or len(filters) < 1:
                finded = True
            else:
                for ftl in filters:
                    satisfied = False 
                    if ftl.type == "AttrCon":
                        if not el.hasAttribute(ftl.name):
                            info = ">> 条件格式错误：节点[%s]没有[%s]属性" % (el.nodeName,ftl.name)
                            lg.myloger.error(info)
                            return None,info
                        else:
                            value = el.getAttribute(ftl.name)
                            if value != ftl.value:
                                break
                            else:
                                info = "get fltobj value[%s],flt value [%s]" %(value,ftl.value)
                                lg.myloger.error(info)
                                satisfied = True
                    else:
                        subs = el._get_childNodes()
                        if subs is None:
                            info = ">> 条件格式错误：节点[%s]没有文本节点" % (el.nodeName)
                            lg.myloger.error(info)
                            return None,info
                        hasText = False
                        for sub in subs:
                            if sub.nodeType == Node.TEXT_NODE:
                                hasText = True
                                if sub.data == ftl.value:
                                    satisfied = True
                                break
                        if not hasText:
                            info = ">> 条件格式错误：节点[%s]没有文本节点" % (el.nodeName)
                            lg.myloger.error(info)
                            return None,info
                    if  satisfied:
                        finded = True
                        break
            if finded:
                info = "find a node %s" % el
                lg.myloger.info(info)
                tarNodes.append(el)
        if len(tarNodes) > 1:
            info = ">> 条件格式错误：命中多个节点"
            lg.myloger.error(info)
            return None
        elif len(tarNodes) == 0:
            info = ">> 条件格式错误：未命中节点"
            lg.myloger.error(info)
            return None,info
        else:
            return tarNodes[0],""

    #读取节点值
    def __getitemvalue(self, tarnode:Element, keystr:str):
        '''读取节点的属性值
            传入参数：
                tarnode：取值目标节点
                keystr：取值定义串，如取节点属性，格式为"AttrCon@AttrName";如取节点文本串，格式为"NodeCon@_",
                        其中AttrName用实际属性名代替，"AttrCon"和"NodeCon"为类型
            返回值：返回属性的取值或文本串，类型为字符串
        '''
        keys = keystr.split(self.__con_innerfilter)
        if len(keys) != 2:
            info = ">> 取值参数[%s]配置格式错误," % keystr
            lg.myloger.error(info)
            return None,info
        if keys[0] == "AttrCon":
            if not tarnode.hasAttribute(keys[1]):
                info = ">> 取值参数[%s]配置错误：节点[%s]无属性域[%s]" % (keystr,tarnode.nodeName,keys[1])
                lg.myloger.error(info)
                return None,info
            else:
                return tarnode.getAttribute(keys[1]),""
        else:
            subs = tarnode._get_childNodes()
            if subs is None:
                info = ">> 条件格式错误：节点[%s]没有文本节点" % (tarnode.nodeName)
                lg.myloger.error(info)
                return None,info
            hasText = False
            for sub in subs:
                if sub.nodeType == Node.TEXT_NODE:
                    hasText = True
                    return sub.data,""
            if not hasText:
                info = ">> 条件格式错误：节点[%s]没有文本节点" % (tarnode.nodeName)
                lg.myloger.error(info)
                return None,info
    
    def __setitemvalue(self, tarnode, keystr,value):
        '''读取节点的属性值
            传入参数：
                tarnode：取值目标节点
                keystr：取值定义串，如取节点属性，格式为"AttrCon@AttrName";如取节点文本串，格式为"NodeCon@_",
                        其中AttrName用实际属性名代替，"AttrCon"和"NodeCon"为类型
                value：设置值，类型为字符串
            返回值：设置成果则返回True，设置错误则返回False，参数错误返回None
            注意事项：本方法调用并未写文件，需随后调用写文件操作放可生效
        '''
        keys = keystr.split(self.__con_innerfilter)
        if len(keys) != 2:
            info = ">> 取值参数[%s]配置格式错误," % keystr
            lg.myloger.error(info)
            return None,info
        if keys[0] == "AttrCon":
            if not tarnode.hasAttribute(keys[1]):
                info = ">> 取值参数[%s]配置错误：节点[%s]无属性域[%s]" % (keystr,tarnode.nodeName,keys[1])
                lg.myloger.error(info)
                return None,info
            else:
                return tarnode.setAttribute(keys[1],value),""
        else:
            tarnode.firstChild.data = value
            return True,""

    def get_encoding(self,cfgpath):
        # 二进制方式读取，获取字节数据，检测类型
        with open(cfgpath, 'rb') as f:
            data = f.read()
            return chardet.detect(data)['encoding']

    #读取xml项的值
    def readvalue(self, nodestr:str, fltstr:str, keystr:str, default = ""):  
        '''读取节点的属性值
            传入参数：
                nodestr：节点串，为"根节点@@子节点@@子节点@@...@@子节点"
                filtstr：配置条件串，格式为"Node1_Name|AttrCon@Attr_Name@value#AND#NodeCoN@_@value@@Node2_Name|AttrCon@Attr_Name@value#AND#NodeCoN@_@value"
                keystr：取值定义串，如取节点属性，格式为"AttrCon@AttrName";如取节点文本串，格式为"NodeCon@_",
                        其中AttrName用实际属性名代替，"AttrCon"和"NodeCon"为类型
            返回值：返回属性的取值或文本串，过程出错返回None，无法匹配返回缺省值
        '''
        stinfo = ">>=====开始读取xml值======"
        lg.myloger.info(stinfo)
        stinfo ="cfgpath:%s nodestr:%s filtstr:%s keystr:%s default:%s" %(self.__cfgpath,nodestr,fltstr,keystr,default)
        lg.myloger.info(stinfo)

        if not self.__hasfile:
            info = ">> 无此文件，请核对路径[%s]" % self.__cfgpath
            lg.myloger.error(stinfo)
            return False,info,None

        temp_list = nodestr.split(self.__node_splitstr)
        dict_nodeflts,info = self.__compilecon__(fltstr)
        if dict_nodeflts is None:
            lg.myloger.error(stinfo)
            return False,info,None
        
        if len(temp_list) < 1:
            if len(dict_nodeflts) > 1:
                info = "节点字典个数不匹配"
                lg.myloger.error(info)
                return False,info,None
            else:
                value,info = self.__getitemvalue(self.__documentElement, keystr)
                lg.myloger.info(info)
                return False,info,value
        else:
            currNode = self.__documentElement
            for nodeName in temp_list:
                subnodes = currNode.getElementsByTagName(nodeName)
                if subnodes is None or len(subnodes) == 0:
                    info = ">> 节点参数[%s]配置错误，节点[%s]不存在" % (nodestr, nodeName)
                    lg.myloger.error(info)
                    return False,info,None
                else:
                    fltpair = None
                    subnode = None
                    if nodeName in dict_nodeflts.keys():
                        fltpair = dict_nodeflts[nodeName]
                        subnode,nodeinfo = self.__getnode(subnodes, fltpair.filters)
                    else:
                        subnode,nodeinfo = self.__getnode(subnodes, None)

                    if subnode is None:
                        info = (">> 节点参数[%s]配置错误，无法在节点列表[%s]中定位节点,错误信息:%s" % (fltpair, subnodes,nodeinfo))
                        lg.myloger.error(info)
                        return False,info,None
                    else:
                        if temp_list[-1] != nodeName:
                            currNode = subnode
                        else:
                            value,info = self.__getitemvalue(subnode, keystr)
                            if value is None:
                                return False,info,None
                            else:
                                return True,info,value
        lg.myloger.info("返回缺省值")                    
        return True,"缺省值",default
    
    
    def setvalue(self, nodestr:str, fltstr:str, keystr:str, value:str):
        '''设置节点的属性值
            传入参数：
                nodestr：节点串，为"根节点@@子节点@@子节点@@...@@子节点"
                filtstr：配置条件串，格式为"Node1_Name|AttrCon@Attr_Name@value#AND#NodeCoN@_@value@@Node2_Name|AttrCon@Attr_Name@value#AND#NodeCoN@_@value"
                keystr：取值定义串，如取节点属性，格式为"AttrCon@AttrName";如取节点文本串，格式为"NodeCon@_",
                        其中AttrName用实际属性名代替，"AttrCon"和"NodeCon"为类型
                value：设置目标值
            返回值：设置成果则返回True，设置错误则返回False，参数错误返回None
            注意事项：本方法调用并未写文件，需随后调用写文件操作放可生效
        '''
        stinfo = ">>=====开始设置xml值======"
        lg.myloger.info(stinfo)
        stinfo ="cfgpath:%s nodestr:%s fltstr:%s keystr:%s value:%s" %(self.__cfgpath,nodestr,fltstr,keystr,value)
        lg.myloger.info(stinfo)

        if not self.__hasfile:
            info = ">> 无此文件，请核对路径[%s]" % self.__cfgpath
            lg.myloger.error(info)
            return False,info 
        
        temp_list = nodestr.split(self.__node_splitstr)
        dict_nodeflts,info = self.__compilecon__(fltstr)
        if dict_nodeflts is None:
            lg.myloger.error(info)
            return False,info
        setted = False
        if len(temp_list) < 1:
            if len(dict_nodeflts) > 1:
                info= ">> 节点参数[%s]配置错误，取根节点数据却设置过滤条件[%s]" % (nodestr, fltstr)
                lg.myloger.error(info)
                return False,info
            else:
                ret,info = self.__setitemvalue(self.__documentElement, keystr,value)
                setted = True
                if ret is True:
                    lg.myloger.info("设置成功")
                else:
                    lg.myloger.error("设置失败")
        else:
            currNode = self.__documentElement
            for nodeName in temp_list:
                subnodes = currNode.getElementsByTagName(nodeName)
                if len(subnodes) == 0:
                    info = ">> 节点参数[%s]配置错误，节点[%s]不存在" % (nodestr, nodeName)
                    lg.myloger.error(info)
                    return False,info
                else:
                    fltpair = None
                    subnode = None
                    if nodeName in dict_nodeflts.keys():
                        fltpair = dict_nodeflts[nodeName]
                        subnode,nodeinfo = self.__getnode(subnodes, fltpair.filters)
                    else:
                        subnode,nodeinfo = self.__getnode(subnodes, None)

                    if subnode is None:
                        info(">> 节点参数[%s]配置错误，无法在节点列表[%s]中定位节点,错误信息" % (fltpair, subnodes,nodeinfo))
                        lg.myloger.error(info)
                        return False,info
                    else:
                        if temp_list[-1] != nodeName:
                            currNode = subnode
                        else:
                            self.__setitemvalue(subnode, keystr,value)
                            setted = True
        return setted,""
        
    #写入配置文件
    def save(self):
        with open(os.path.join(self.__cfgpath), 'w', encoding=self._encoding) as fh:
            self.__domtree.writexml(fh)
        