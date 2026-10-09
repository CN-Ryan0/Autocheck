# -*- coding: utf-8 -*-
"""
XML 文件解析模块
提供对巡检 XML 文件的解析功能，支持获取项目、应用、资产ID等信息，
以及通过 XPath 查询 section、member、node 等元素。

@author: Ryan和他的小伙伴们
@date: 2026-06-12
@version: 2.0
"""

try:
    from lxml import etree
    USE_LXML = True
except ImportError:
    import xml.etree.ElementTree as etree
    USE_LXML = False


class XmlParser:
    """XML 文件解析器，封装常用查询方法"""

    def __init__(self, sourcepath):
        """
        初始化解析器
        :param sourcepath: XML 文件路径
        """
        self.sourcepath = sourcepath
        self.source_etree_obj = None
        self.root = None

        try:
            self.source_etree_obj = etree.parse(sourcepath)
            self.root = self.source_etree_obj.getroot()
        except Exception as e:
            print(f" * [错误] XML 文件解析出错 --> {sourcepath}，原因：{e}")

    @property
    def get_version(self):
        """XML 版本号"""
        if self.source_etree_obj:
            return self.source_etree_obj.docinfo.xml_version
        return None

    @property
    def get_encoding(self):
        """XML 编码"""
        if self.source_etree_obj:
            return self.source_etree_obj.docinfo.encoding
        return None

    @property
    def get_project(self):
        """项目名称"""
        if self.root is not None:
            elem = self.root.find("project")
            if elem is not None and elem.text:
                return elem.text.strip()
        return None

    @property
    def get_application(self):
        """业务系统名称"""
        if self.root is not None:
            elem = self.root.find("application")
            if elem is not None and elem.text:
                return elem.text.strip()
        return None

    @property
    def get_assetid(self):
        """资产ID"""
        if self.root is not None:
            elem = self.root.find("assetid")
            if elem is not None and elem.text:
                return elem.text.strip()
        return None

    @property
    def get_section_list(self):
        """所有 section 元素列表"""
        if self.root is not None:
            return self.root.xpath("//section")
        return []

    @property
    def get_member_list(self):
        """所有 member 元素列表"""
        if self.root is not None:
            return self.root.xpath("//member")
        return []

    @property
    def get_node_list(self):
        """所有 node 元素列表"""
        if self.root is not None:
            return self.root.xpath("//node")
        return []

    @property
    def get_all_section_id(self):
        """所有 section 的 id 属性值列表"""
        return [sec.attrib.get('id') for sec in self.get_section_list if 'id' in sec.attrib]

    @property
    def get_all_member_key(self):
        """所有 member 的 key 属性值列表"""
        return [mem.attrib.get('key') for mem in self.get_member_list if 'key' in mem.attrib]

    @property
    def get_all_node_key(self):
        """所有 node 的 key 属性值列表"""
        return [node.attrib.get('key') for node in self.get_node_list if 'key' in node.attrib]

    def get_section(self, section_id):
        """根据 id 获取 section 元素"""
        if self.root is None:
            return []
        result = self.root.xpath(f"//section[@id='{section_id}']")
        return result if result else []

    def get_member(self, key):
        """根据 key 获取 member 的文本内容"""
        if self.root is None:
            return None
        result = self.root.xpath(f"//member[@key='{key}']")
        if result and result[0].text is not None:
            return result[0].text.strip()
        return None

    def get_node(self, mkey, nkey):
        """根据 member key 和 node key 获取 node 的文本内容"""
        if self.root is None:
            return None
        result = self.root.xpath(f"//member[@key='{mkey}']/node[@key='{nkey}']")
        if result and result[0].text is not None:
            return result[0].text.strip()
        return None
