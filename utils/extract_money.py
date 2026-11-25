import re
import traceback

CURRENCY_CASE = r'(块(钱)?(人民币)?|元((人民|港|日|澳|韩|(新)?台)币)?|(人民|港|日|澳|韩|(新)?台)币|圆(整)?|' \
                r'(美|港|澳门|日|韩|缅|马|新加坡|欧|加|新西兰|澳|澳大利亚)元|美(金|刀)|英镑|马克|法郎|卢布|泰铢)'

MONEY_PREFIX_STRING = r'((将)?近|只有|仅|(大)?约(莫|合)?|大概|至少(要)?|不(到|足|超过)?|逾|高于|(高)?达(到)?|^上|(超)?过|超)'
MONEY_SUFFIX_STRING = r'(以上|以下|左右|上下)'

MONEY_BLUR_STRING = r'((大)?约(莫|合)?|大概|左右|上下)'
MONEY_MINUS_STRING = r'((将)?近|不(到|足|超过)?|以下)'
MONEY_PLUS_STRING = r'(至少(要)?|逾|高于|上|(超)?过|超|以上)'

MONEY_NUM_MIDDLE_STRING = r'[,， ]'

MONEY_NUM_STRING = r'^[ \.多个数几百佰k千仟w万萬亿十拾兆〇O0-9零０-９一二两三四五六七八九壹弌贰弍俩叁弎仨肆伍陆柒捌玖]+$'

MONEY_KUAI_MAO_JIAO_FEN_STRING = r'[分角毛块]'
MONEY_PREFIX_CASE_STRING = r'(港币|人民币|(新)?台币)'

MONEY_SUFFIX_CASE_STRING = r'((分|角|毛|块|元)钱?|(人民|港|日|澳|(新)?台)币|圆(整)?|英镑|美(金|分|刀)|马克|法郎|卢布|泰铢|' \
                           r'元((人民|港|日|澳|韩|(新)?台)币)?|(美|港|澳门|日|韩|缅|马|新加坡|欧|加|加拿大|新西兰|澳|澳大利亚)元|' \
                           r'(越(南)?)盾|雷亚尔)'

MONEY_CHAR_STRING = r'(?!(余|多|分|角|不|块|〇))' \
                    r'((将)?近|只有|仅|(大)?约(莫|合)?|大概|至少(要)?|不(到|足|超过)?|逾|高于|(高)?达(到)?|^上|(超)?过|超|' \
                    r'以上|以下|左右|上下|港币|人民币|(新)?台币|(分|角|毛|块|元)钱?|(人民|港|日|澳|(新)?台)币|圆(整)?|英镑|' \
                    r'美(金|分|刀)|马克|法郎|卢布|泰铢|元((人民|港|日|澳|韩|(新)?台)币)?|(美|港|澳门|日|韩|缅|马|新加坡|欧|' \
                    r'加|加拿大|新西兰|澳|澳大利亚)元|(越(南)?)盾|雷亚尔|' \
                    r'[分角毛块 \.\,\-\~—－～，余多个数几百佰k千仟w万萬亿十拾兆〇O0-9零０-９一二两三四五六七八九壹弌贰弍俩叁弎仨肆伍陆柒捌玖\(\)（）不含])+'


def start_end(regular_expression):
    return ''.join([r'^', regular_expression, r'$'])


PARENTHESES_PATTERN = '{}「」[]【】()（）<>《》〈〉『』〔〕｛｝＜＞〖〗'


class Extractor(object):
    """ 规则抽取器 """

    def __init__(self):
        self.money_pattern = None
        self.email_pattern = None
        self.email_domain_pattern = None
        self.email_prefix_pattern = None
        self.url_pattern = None
        self.phone_number_pattern = None
        self.ip_address_pattern = None
        self.id_card_pattern = None
        self.html_tag_pattern = None
        self.qq_pattern = None
        self.strict_qq_pattern = None
        self.wechat_id_pattern = None
        self.strict_wechat_id_pattern = None
        self.cell_phone_pattern = None
        self.landline_phone_pattern = None
        self.phone_prefix_pattern = None
        self.extract_parentheses_pattern = None
        self.remove_parentheses_pattern = None
        self.parentheses_pattern = PARENTHESES_PATTERN
        self.parentheses_dict = None
        self.redundant_pattern = None
        self.exception_pattern = None
        self.full_angle_pattern = None
        self.chinese_char_pattern = None
        self.chinese_chars_pattern = None
        self.motor_vehicle_licence_plate_pattern = None

    @staticmethod
    def _extract_base(pattern, text, with_offset=False):
        """ 正则抽取器的基础函数

        Args:
            pattern(re.compile): 正则表达式对象
            text(str): 字符串文本
            with_offset(bool): 是否携带 offset （抽取内容字段在文本中的位置信息）

        Returns:
            list: 返回结果

        """
        if with_offset:
            results = [{'text': item.group(1),
                        'offset': (item.span()[0] - 1, item.span()[1] - 1)}
                       for item in pattern.finditer(text)]
        else:
            results = [item.group(1) for item in pattern.finditer(text)]

        return results

    def extract_parentheses(self, text, parentheses=PARENTHESES_PATTERN, detail=False):
        """ 提取文本中的括号及括号内内容，当有括号嵌套时，提取每一对
        成对的括号的内容

        Args:
            text(str): 字符串文本
            parentheses: 要删除的括号类型，格式为:
                '左括号1右括号1左括号2右括号2...'，必须为成对的括号如'{}()[]'，
                默认为self.parentheses
            detail: 是否打印括号内容位置信息

        Returns:
            list: [
                    {
                        'context'(str): 'the context between parentheses',
                        'offset'(tuple): 'the location of extracted text'
                    },  # 当 detail 为 True 时
                    'the context between parentheses',  # 当 detail 为 False 时
                    ...
                ]

        """
        if self.extract_parentheses_pattern is None or self.parentheses_pattern != parentheses:
            self.parentheses_pattern = parentheses

            extract_pattern = '[' + re.escape(self.parentheses_pattern) + ']'
            extract_pattern = re.compile(extract_pattern)

            p_length = len(self.parentheses_pattern)

            parentheses_dict = dict()
            for i in range(0, p_length, 2):
                value = self.parentheses_pattern[i]
                key = self.parentheses_pattern[i + 1]
                parentheses_dict.update({key: value})

            self.parentheses_dict = parentheses_dict
            self.extract_parentheses_pattern = extract_pattern

        content_list = []
        parentheses_list = []
        idx_list = []
        finditer = self.extract_parentheses_pattern.finditer(text)
        for i in finditer:
            idx = i.start()
            parentheses = text[idx]

            if parentheses in self.parentheses_dict.keys():
                if len(parentheses_list) > 0:
                    if parentheses_list[-1] == self.parentheses_dict[parentheses]:
                        parentheses_list.pop()
                        if detail:
                            start_idx = idx_list.pop()
                            end_idx = idx + 1
                            content_list.append(
                                {'content': text[start_idx: end_idx],
                                 'offset': (start_idx, end_idx)})
                        else:
                            content_list.append(text[idx_list.pop(): idx + 1])
            else:
                parentheses_list.append(parentheses)
                idx_list.append(idx)

        return content_list

    def remove_parentheses(self, text, parentheses=PARENTHESES_PATTERN):
        """ 删除文本中的括号及括号内内容

        Args:
            text(str): 字符串文本
            parentheses: 要删除的括号类型，格式为:
                '左括号1右括号1左括号2右括号2...'，必须为成对的括号如'{}()[]'，
                默认为self.parentheses

        Returns:
            str: 删除括号及括号中内容后的文本

        """
        if self.remove_parentheses_pattern is None or self.parentheses_pattern != parentheses:
            self.parentheses_pattern = parentheses

            p_length = len(self.parentheses_pattern)
            remove_pattern_list = list()
            remove_pattern_format = '{left}[^{left}{right}]*{right}'

            for i in range(0, p_length, 2):
                left = re.escape(self.parentheses_pattern[i])
                right = re.escape(self.parentheses_pattern[i + 1])
                remove_pattern_list.append(
                    remove_pattern_format.format(left=left, right=right))

            remove_pattern = '|'.join(remove_pattern_list)
            remove_pattern = re.compile(remove_pattern)

            self.remove_parentheses_pattern = remove_pattern

        length = len(text)
        while True:
            text = self.remove_parentheses_pattern.sub('', text)
            if len(text) == length:
                return text
            length = len(text)


extractor = Extractor()
extract_parentheses = extractor.extract_parentheses
remove_parentheses = extractor.remove_parentheses


class MoneyParser(object):
    def __init__(self):
        self.money_pattern_1 = None

    def _prepare(self):
        self.float_num_pattern = re.compile('\d+(\.)?\d*')
        self.punc_pattern = re.compile(MONEY_NUM_MIDDLE_STRING)
        self.bai_pattern = re.compile('百|佰')
        self.qian_pattern = re.compile('千|仟|k')
        self.wan_pattern = re.compile('万|萬|w')
        self.yi_pattern = re.compile('亿')
        self.chinese_yuan_currency_pattern = re.compile('(块钱|元|块)')
        self.chinese_jiao_currency_pattern = re.compile('(角|毛)')
        self.currency_case_pattern = re.compile(CURRENCY_CASE)
        # self.currency_case_pattern = re.compile(MONEY_SUFFIX_CASE_STRING)
        # self.chinese_kuai_jiao_mao_fen_pattern = re.compile(MONEY_KUAI_MAO_JIAO_FEN_STRING)

        self.money_modifier_pattern = re.compile(
            MONEY_PREFIX_STRING[:-1] + '|' + MONEY_SUFFIX_STRING[1:])

        # 判断货币金额精确度
        self.money_blur_pattern = re.compile(start_end(MONEY_BLUR_STRING))
        self.money_minus_pattern = re.compile(start_end(MONEY_MINUS_STRING))
        self.money_plus_pattern = re.compile(start_end(MONEY_PLUS_STRING))

        self.zero_seg_pattern = re.compile(r'0+\.00')

        # 检测货币金额数值是否符合要求，不符合要求将直接报错，必须为数值字符与单位字符，可包括 角、分等
        self.money_num_string_pattern = re.compile(
            ''.join([MONEY_NUM_STRING[:-3], '元钱', MONEY_KUAI_MAO_JIAO_FEN_STRING[1:], '+$']))

        # 纯数字的金额
        self.money_pattern_1 = re.compile(r'^\d+(\.)?\d*$')
        # 前为数字，后为汉字的金额
        self.money_pattern_2 = re.compile(r'^\d+(\.)?\d*[十拾百佰k千仟w万萬亿兆]{1,2}$')

        self.multi_nums = {
            '分': 0.01, '角': 0.1, '毛': 0.1, '十': 10, '拾': 10,
            '百': 100, '佰': 100, '千': 1000, '仟': 1000,
            '万': 10000, '萬': 10000, '亿': 100000000}
        self.plus_nums = {
            '〇': 0, 'O': 0, '零': 0, '０': 0,
            '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
            '壹': 1, '弌': 1, '贰': 2, '弍': 2, '俩': 2, '叁': 3, '弎': 3, '仨': 3, '肆': 4, '伍': 5, '陆': 6, '柒': 7,
            '捌': 8, '玖': 9,
            '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            '１': 0, '２': 2, '３': 3, '４': 4, '５': 5, '６': 6, '７': 7, '８': 8, '９': 9,
        }
        self.suffix_nums = {
            '百': 100, '佰': 100, '千': 1000, '仟': 1000, 'k': 1000,
            '万': 10000, '萬': 10000, 'w': 10000, '亿': 100000000,
            '十万': 100000, '拾万': 100000, '百万': 1000000, '佰万': 1000000,
            '仟万': 10000000, '千万': 10000000, '万万': 100000000, '萬萬': 100000000,
            '十亿': 1000000000, '拾亿': 1000000000, '百亿': 10000000000, '佰亿': 10000000000,
            '千亿': 100000000000, '仟亿': 100000000000, '万亿': 1000000000000, '萬亿': 1000000000000,
            '兆': 1000000000000}

        self.sequential_char_num_pattern = re.compile(
            r'(一二|二三|两三|三四|三五|四五|五六|六七|七八|八九|'
            r'壹贰|弌弍|贰叁|贰弎|弍弎|贰仨|两叁|两弎|两仨|叁肆|弎肆|仨肆|叁伍|弎伍|仨伍|肆伍|伍陆|陆柒|柒捌|捌玖)')

        self.alias_RMB_case = {'块钱人民币', '块钱', '人民币', '块', '元人民币', '圆', '圆整'}
        self.alias_HK_case = {'港币', '元港币'}
        self.alias_JP_case = {'日币', '元日币'}
        self.alias_KR_case = {'韩币', '元韩币'}
        self.alias_TW_case = {'台币', '元新台币', '元台币'}
        self.alias_AUS_case = {'澳大利亚元', '澳币', '元澳币'}
        self.alias_USA_case = {'美刀', '美金'}

        self.standard_format = '{:.2f}'
        self.type_error = 'the given money_string `{}` is illegal.'

    def turn_num_standard_format(self, num):
        """将数字形式转换成`std_fmt`形式。
        使用该函数将数字形式转换成 `std_fmt` 形式。

        Args:
            num(int|str|float): 一个数字，支持 int 或 str 格式。

        Returns:
            转换后`std_fmt`形式的 str 类型的数字。

        Examples:
            >>> print(self.turn_num_standard_format(30.5))

            # '30.50'

        """
        standard_num = None

        if type(num) is str:
            if self.money_pattern_1.match(num):
                standard_num = self.standard_format.format(float(num))

        elif type(num) is int or type(num) is float:
            standard_num = self.standard_format.format(num)

        # else:
        #     raise TypeError('the type of `num` {} is not in [str, int, float].'.format(num))

        return standard_num

    def turn_money_std_fmt_util1(self, money_string):
        """将中文金额形式转换成 float 形式。处理以 “千百十个” 为核心的金额字符串。

        使用该函数将中文金额转换成易于计算的 float 形式，注意该函数是 turn_money_std_fmt
        辅助函数，只能方便将一万这种转换，一千万无法转换。

        Args:
            money_string: 一个中文格式表示的金额。

        Returns:
            转换后 float 类型的数字。

        """

        rtn_std_num = 0.0
        if not money_string or type(money_string) is not str:
            return rtn_std_num

        # 对 `十、百、千` 开头数字进行规范化
        if money_string[0] in '十拾百佰千仟':
            money_string = '一' + money_string

        # 对角、分进行规范化
        if self.chinese_yuan_currency_pattern.search(money_string):
            jiao_fen = self.chinese_yuan_currency_pattern.split(money_string)[-1]
            if self.chinese_jiao_currency_pattern.search(jiao_fen):
                fen = self.chinese_jiao_currency_pattern.split(jiao_fen)[-1]
                if '分' not in fen and len(fen) == 1:
                    # 分 字符串无“分”字且长度为 1
                    money_string = money_string + '分'
            else:
                if '角' not in jiao_fen and len(jiao_fen) == 1:
                    # 即 角分 字符串仅有一个字符，即角的数字
                    money_string = money_string + '角'

        # 两个除零外的 plus_num 不可以连续

        tmp_nums = list()
        for char in list(money_string):
            plus_num = self.plus_nums.get(char, 0)
            if plus_num != 0:
                tmp_nums.append(plus_num)

            multi_num = self.multi_nums.get(char, 1)
            if len(tmp_nums) >= 1:
                tmp_nums[-1] = tmp_nums[-1] * multi_num

        rtn_std_num = sum(tmp_nums)
        return rtn_std_num

    def turn_money_std_fmt_util2(self, money_string):
        """将中文金额形式转换成 float 形式。处理以 “万” 为核心的金额字符串

        使用该函数将中文金额转换成易于计算的 float 形式，注意该函数是 turn_money_std_fmt 的
        另一个辅助函数，与 turn_money_std_fmt_util1 搭配起来转换类似“1千万”数字。

        Args:
            money_string: 一个中文格式表示的金额。

        Returns:
            转换后 float 类型的数字。

        """
        if '万' in money_string or '萬' in money_string:
            if money_string[0] in '万萬':
                money_string = '一' + money_string

            seg_money_string = self.wan_pattern.split(money_string)
            if len(seg_money_string) == 2:
                prev, nxt = seg_money_string
                tmp_prev_num = self.turn_money_std_fmt_util1(prev)
                tmp_prev_num = tmp_prev_num * 10000
                tmp_nxt_num = self.turn_money_std_fmt_util1(nxt)
                rtn_std_num = tmp_prev_num + tmp_nxt_num
            else:
                raise ValueError(self.type_error.format(money_string))
        else:
            rtn_std_num = self.turn_money_std_fmt_util1(money_string)

        return rtn_std_num

    def turn_money_std_fmt_util3(self, money_string):
        """将中文金额形式转换成 float 形式。处理以 “亿” 为核心的金额字符串

        使用该函数将中文金额转换成易于计算的 float 形式，注意该函数是 turn_money_std_fmt 的
        另一个辅助函数，与 turn_money_std_fmt_util2 搭配起来转换类似“1千亿”数字。

        Args:
            money_string: 一个中文格式表示的金额。

        Returns:
            转换后 float 类型的数字。

        """
        if '亿' in money_string:
            if money_string.startswith('亿'):
                money_string = '一' + money_string

            seg_billion = self.yi_pattern.split(money_string)
            if len(seg_billion) == 2:
                prev, nxt = seg_billion
                prev_num = self.turn_money_std_fmt_util2(prev)
                nxt_num = self.turn_money_std_fmt_util2(nxt)
                rtn_std_num = prev_num * 100000000 + nxt_num

            else:
                raise ValueError(self.type_error.format(money_string))
        else:
            rtn_std_num = self.turn_money_std_fmt_util2(money_string)

        return rtn_std_num

    def _get_currency_case(self, money_string, default_unit='元'):
        """ 获取金额中的货币类型 """
        res_list = [item for item in self.currency_case_pattern.finditer(money_string)]

        if len(res_list) == 0:
            return default_unit, money_string  # 默认是人民币元

        elif len(res_list) in {1, 2}:
            # 存在一种特殊情况，即 “三万元欧元”，可以得到 res_list 长度为2，但它其实只属于欧元
            matched_case = False
            if len(res_list) == 2:
                first_res = res_list[0]
                second_res = res_list[1]
                if first_res.group() == '元' and (first_res.span()[1] == second_res.span()[0]):
                    matched_case = True
                    # 第一个字符是 元，且两个单位相邻，则选取后一个单位作为真正的货币单位
                    unit = second_res.group()
                    money_string = money_string.replace('元', '', 1)
                    money_string = self.currency_case_pattern.sub('', money_string)
                    return unit, money_string

            if not matched_case:
                # 除此之外，它按以下条件进行解析
                # 即，要么是首词，要么是末尾词
                res = res_list[0]
                currency_unit = res.group()
                # 规定标准的货币类型
                if currency_unit in self.alias_RMB_case:
                    unit = '元'
                elif currency_unit in self.alias_HK_case:
                    unit = '港元'
                elif currency_unit in self.alias_JP_case:
                    unit = '日元'
                elif currency_unit in self.alias_KR_case:
                    unit = '韩元'
                elif currency_unit in self.alias_TW_case:
                    unit = '新台币'
                elif currency_unit in self.alias_AUS_case:
                    unit = '澳元'
                elif currency_unit in self.alias_USA_case:
                    unit = '美元'
                else:
                    unit = currency_unit

                # 切去货币类型，保留数额，但不包括 角、分
                if len(res_list) == 1:
                    if res.span()[1] == len(money_string) or res.span()[0] == 0:
                        # 货币在首部、或尾部
                        money_string = self.currency_case_pattern.sub('', money_string)
                        return unit, money_string
                    else:
                        # 不在首部、尾部，说明尾部还有分、角等
                        # 若字符串中还不包含 分角毛 等字符，说明这个金额文本有误，如“70000元 2022”
                        if ('分' not in money_string) and ('角' not in money_string) and ('毛' not in money_string):
                            raise ValueError(self.type_error.format(money_string))
                        return unit, money_string

                elif len(res_list) == 2:
                    if res.span()[0] != 0:
                        raise ValueError(self.type_error.format(money_string))

                    if res_list[1].span()[1] == len(money_string):
                        money_string = self.currency_case_pattern.sub('', money_string)
                        return unit, money_string

                    else:
                        # 不在首部、尾部，说明尾部还有分、角等
                        # 若字符串中还不包含 分角毛 等字符，说明这个金额文本有误，如“70000元 2022”
                        if ('分' not in money_string) and ('角' not in money_string) and ('毛' not in money_string):
                            raise ValueError(self.type_error.format(money_string))

                        money_string = self.currency_case_pattern.sub('', money_string, 1)
                        return unit, money_string

        else:
            raise ValueError(self.type_error.format(money_string))

    def _cleansing(self, money_string):
        # 去除其中的标点符号 ，,等
        money_string = self.punc_pattern.sub('', money_string)

        # 去除其中的括号，如 “50万元（含）以上”
        sub_parentheses = extract_parentheses(money_string, parentheses='()（）')
        if '含' in ''.join(sub_parentheses):
            money_string = remove_parentheses(money_string, parentheses='()（）')

        return money_string

    def _definition(self, money_string):
        """判断货币金额的精确度，为精确，或模糊"""

        modifiers = [item.group() for item in self.money_modifier_pattern.finditer(money_string)]

        if len(modifiers) == 0:
            minus_res, plus_res, blur_res = None, None, None

        elif len(modifiers) == 1:
            # 仅一个前缀或后缀
            blur_res = self.money_blur_pattern.search(modifiers[0])
            minus_res = self.money_minus_pattern.search(modifiers[0])
            plus_res = self.money_plus_pattern.search(modifiers[0])

        elif len(modifiers) == 2:
            # 分别有一个前缀和后缀
            blur_res_1 = self.money_blur_pattern.search(modifiers[0])
            minus_res_1 = self.money_minus_pattern.search(modifiers[0])
            plus_res_1 = self.money_plus_pattern.search(modifiers[0])
            blur_res_2 = self.money_blur_pattern.search(modifiers[1])
            minus_res_2 = self.money_minus_pattern.search(modifiers[1])
            plus_res_2 = self.money_plus_pattern.search(modifiers[1])

            blur_res = blur_res_1 or blur_res_2
            minus_res = minus_res_1 or minus_res_2
            plus_res = plus_res_1 or plus_res_2

        else:
            # 多余两个词缀，说明金额字符串有误
            raise ValueError(self.type_error.format(money_string))

        definition = 'accurate'
        if minus_res:  # 确定 minus_res 与 plus_res 不冲突，不同时 not None
            definition = 'blur-'
        elif plus_res:
            definition = 'blur+'
        elif blur_res:
            definition = 'blur'

        money_string = self.money_modifier_pattern.sub('', money_string)
        return money_string, definition

    def _accuracy(self, money_string, definition):
        """ 处理模糊金额，如 “六千多万日元”、“十几块钱”、“数十元”、“十多块钱” 等 """
        if '多' in money_string:
            money_string = money_string.replace('多', '')
            definition = 'blur+span'
            return money_string, definition

        if '余' in money_string:
            money_string = money_string.replace('余', '')
            definition = 'blur+span'
            return money_string, definition

        if '几' in money_string or '数' in money_string:
            if money_string[0] in '几数':
                money_string = money_string.replace('几', '').replace('数', '')
                definition = 'blur++span'
            else:
                money_string = money_string.replace('几', '').replace('数', '')
                definition = 'blur+span'
            return money_string, definition

        return money_string, definition

    def _expand_sequential_string(self, money_string):
        """ 对某些字符串进行扩展，如 “五六百美元” 需要扩展为 “五到六百美元” """
        if self.sequential_char_num_pattern.search(money_string):
            sequential_string = self.sequential_char_num_pattern.search(money_string).group()
            money_string_pattern = self.sequential_char_num_pattern.sub('{}', money_string)
            sub_token = sequential_string[0] + '到' + sequential_string[1]
            money_string = money_string_pattern.format(sub_token)

        return money_string

    def _compensate_first_money_string(
            self, first_money_string, second_money_string):
        """ 根据情况，对金额范围的第一个金额进行单位补全
        例如： 3到5万港币，被拆分为 3，5万港币，须将 3 补全为 3万港币
        思路：第二个字符串一般为完全字符串，不须补全，
            且默认第二个字符串是 数字、汉字单位混合字符串，
            此时考察第一个字符串，若其数值低于 第二个字符串的数字值，
            则为其添加第二个字符串的汉字单位。


            十八到三十万元
            一百二十到一百五十万元
            一千到两千万元
            一千到两千亿元
            三到五百
            八到九千
        """
        # 先分析第一个字符串的金额，确定其信息，是否需要补全
        if self.money_pattern_1.search(first_money_string):
            first_computed_money_num = float(first_money_string)

        elif self.money_pattern_2.search(first_money_string):
            # 前为数字，后为汉字的金额，如 “6000万”
            # 若第一个字符串属于该种类型，且其 char_part 非空，说明可以直接返回
            char_part = self.float_num_pattern.sub('', first_money_string)
            if char_part in self.suffix_nums:
                return first_money_string
            else:
                raise ValueError(self.type_error.format(first_money_string))

        else:
            # 若第一个字符串有单位，则直接返回结果
            res_list = [item for item in self.currency_case_pattern.finditer(first_money_string)]

            if len(res_list) != 0:
                # 有货币单位
                if res_list[-1].span()[1] == len(first_money_string):
                    # 即第一个字符串末尾为单位，则直接跳过
                    return first_money_string

            first_computed_money_num = self.turn_money_std_fmt_util3(first_money_string)

        # 前置操作，需要重复执行一次，因此较为耗时
        second_money_string = self._cleansing(second_money_string)
        second_money_string, definition = self._definition(second_money_string)
        unit, second_money_string = self._get_currency_case(second_money_string)
        second_money_string, definition = self._accuracy(second_money_string, definition)

        # 分析第二个字符串的类型，并按类型对其进行判断，是否对第一个字符串添加信息
        if self.money_pattern_2.search(second_money_string):
            char_part = self.float_num_pattern.sub('', second_money_string)
            if char_part not in self.suffix_nums:
                raise ValueError(self.type_error.format(second_money_string))

            num_part = second_money_string.replace(char_part, '')
            if self.money_pattern_1.search(num_part):
                second_computed_money_num = float(num_part)
            else:
                raise ValueError(self.type_error.format(second_money_string))

            if first_computed_money_num < second_computed_money_num:
                # 此时需要添加单位
                return first_money_string + char_part
            else:
                return first_money_string

        else:
            if self.yi_pattern.search(second_money_string):
                seg_billion = self.yi_pattern.split(second_money_string)
                if len(seg_billion) == 2:
                    second_computed_money_num = self.turn_money_std_fmt_util2(seg_billion[0])
                else:
                    raise ValueError(self.type_error.format(second_money_string))

                if first_computed_money_num < second_computed_money_num:
                    return first_money_string + '亿'
                else:
                    return first_money_string

            elif self.wan_pattern.search(second_money_string):
                seg_wan = self.wan_pattern.split(second_money_string)
                if len(seg_wan) == 2:
                    second_computed_money_num = self.turn_money_std_fmt_util1(seg_wan[0])
                else:
                    raise ValueError(self.type_error.format(second_money_string))

                if first_computed_money_num < second_computed_money_num:
                    return first_money_string + '万'
                else:
                    return first_money_string

            elif self.qian_pattern.search(second_money_string):
                seg_qian = self.qian_pattern.split(second_money_string)
                if len(seg_qian) == 2:
                    second_computed_money_num = self.turn_money_std_fmt_util1(seg_qian[0])
                else:
                    raise ValueError(self.type_error.format(second_money_string))

                if first_computed_money_num < second_computed_money_num:
                    return first_money_string + '千'
                else:
                    return first_money_string
            elif self.bai_pattern.search(second_money_string):
                seg_bai = self.bai_pattern.split(second_money_string)
                if len(seg_bai) == 2:
                    second_computed_money_num = self.turn_money_std_fmt_util1(seg_bai[0])
                else:
                    raise ValueError(self.type_error.format(second_money_string))

                if first_computed_money_num < second_computed_money_num:
                    return first_money_string + '百'
                else:
                    return first_money_string

            return first_money_string

    def __call__(self, money_string, default_unit='元', ret_format='detail'):

        if self.money_pattern_1 is None:
            self._prepare()

        if not money_string:  # or len(money_string) == 1:
            raise ValueError(self.type_error.format(money_string))

        # 若检测到需要扩展的类型，如 “五六百美元” 需要扩展为 “五到六百美元”
        money_string = self._expand_sequential_string(money_string)

        first_money_string, second_money_string = None, None

        if first_money_string is None or second_money_string is None:
            # 按单金额字符串返回
            return self.parse_single_money(
                money_string, default_unit=default_unit, ret_format=ret_format)

        else:
            first_money_string = self._compensate_first_money_string(
                first_money_string, second_money_string)

            first_money_res = self.parse_single_money(
                first_money_string, default_unit=default_unit, ret_format=ret_format)
            second_money_res = self.parse_single_money(
                second_money_string, default_unit=default_unit, ret_format=ret_format)

            # 将两个货币金额合并
            if ret_format == 'str':
                if type(first_money_res) is str and type(second_money_res) is str:
                    ret_money = [first_money_res, second_money_res]
                elif type(first_money_res) is str and type(second_money_res) is list:
                    ret_money = [first_money_res, second_money_res[1]]
                elif type(first_money_res) is list and type(second_money_res) is str:
                    ret_money = [first_money_res[0], second_money_res]
                elif type(first_money_res) is list and type(second_money_res) is list:
                    ret_money = [first_money_res[0], second_money_res[1]]

            elif ret_format == 'detail':
                first_unit = first_money_res['case']
                second_unit = second_money_res['case']

                if second_unit != '元':
                    unit = second_unit
                elif first_unit != '元':
                    unit = first_unit
                else:
                    unit = '元'

                definition = 'blur'

                if type(first_money_res['num']) is str and type(second_money_res['num']) is str:
                    ret_money = [first_money_res['num'], second_money_res['num']]
                elif type(first_money_res['num']) is str and type(second_money_res['num']) is list:
                    ret_money = [first_money_res['num'], second_money_res['num'][1]]
                elif type(first_money_res['num']) is list and type(second_money_res['num']) is str:
                    ret_money = [first_money_res['num'][0], second_money_res['num']]
                elif type(first_money_res['num']) is list and type(second_money_res['num']) is list:
                    ret_money = [first_money_res['num'][0], second_money_res['num'][1]]

                ret_money = {'num': ret_money, 'case': unit, 'definition': definition}

            return ret_money

    def parse_single_money(self, money_string, default_unit='元', ret_format='detail'):
        """ 解析单个金额字符串，可由解析两个组成金额范围 """

        # 清洗字符串
        money_string = self._cleansing(money_string)

        # 判断金额精确粒度，并清除前置词汇和后置词汇
        money_string, definition = self._definition(money_string)

        # 判断货币类型
        unit, money_string = self._get_currency_case(money_string, default_unit=default_unit)

        # 处理模糊金额，如 “六千多万”、“十几块钱”、“数十元”、“十多块钱”、“2000余元” 等
        money_string, definition = self._accuracy(money_string, definition)

        if money_string == '':
            raise ValueError(self.type_error.format(money_string))

        # 若货币的金额字符串部分有误，则报错返回。
        if self.money_num_string_pattern.search(money_string) is None:
            raise ValueError(self.type_error.format(money_string))
            # pass

        if self.money_pattern_1.search(money_string):
            # 纯数字格式的金额，如 “549040.27”
            computed_money_num = float(money_string)

        elif self.money_pattern_2.search(money_string):
            # 前为数字，后为汉字的金额，如 “6000万”

            char_part = self.float_num_pattern.sub('', money_string)
            if char_part in self.suffix_nums:
                num_suffix = self.suffix_nums.get(char_part)
            else:
                raise ValueError(self.type_error.format(money_string))

            num_part = money_string.replace(char_part, '')
            if self.money_pattern_1.search(num_part):
                computed_money_num = float(num_part) * num_suffix
            else:
                raise ValueError(self.type_error.format(money_string))

        else:
            computed_money_num = self.turn_money_std_fmt_util3(money_string)

        # 金额标准化
        standard_money_num = self.turn_num_standard_format(computed_money_num)
        if standard_money_num is None:
            raise ValueError(self.type_error.format(money_string))

        standard_money_num_list = []
        if 'span' in definition:
            if definition == 'blur+span':
                second_money_num = self._get_second_num(standard_money_num)
            elif definition == 'blur++span':
                second_money_num = self._get_second_num(standard_money_num, flag='++')

            standard_money_num_list = [standard_money_num, second_money_num]
            definition = 'blur'

        # 组织返回格式
        if ret_format == 'str':
            if len(standard_money_num_list) == 0:
                ret_money = standard_money_num + unit
            elif len(standard_money_num_list) == 2:
                ret_money = [standard_money_num_list[0] + unit, standard_money_num_list[1] + unit]
        elif ret_format == 'detail':
            if len(standard_money_num_list) == 0:
                ret_money = {'num': standard_money_num, 'case': unit, 'definition': definition}
            elif len(standard_money_num_list) == 2:
                ret_money = {'num': standard_money_num_list, 'case': unit, 'definition': definition}

        return ret_money

    def _get_second_num(self, num, flag='+'):
        if flag == '+':
            res = self.zero_seg_pattern.search(num)
            if res is not None:
                back_part = res.group()
                front_part = num.replace(back_part, '')
                new_front_part = str(int(front_part) + 1)
                return new_front_part + back_part
            else:
                return None
        elif flag == '++':
            num = float(num) * 10
            standard_money_num = self.turn_num_standard_format(num)
            return standard_money_num


class MoneyExtractor(object):

    def __init__(self):
        self.parse_money = None

    def _prepare(self):
        self.parse_money = MoneyParser()
        # single_money_pattern = ''.join(
        #     [absence(MONEY_PREFIX_STRING),
        #      absence(MONEY_PREFIX_CASE_STRING), '(', MONEY_NUM_STRING, '+',
        #      bracket(MONEY_NUM_MIDDLE_STRING + MONEY_NUM_STRING + '+'), '*',
        #      MONEY_SUFFIX_CASE_STRING, ')+',
        #      bracket_absence(MONEY_NUM_STRING),
        #      absence(MONEY_SUFFIX_STRING)])

        # self.money_string_pattern = re.compile(single_money_pattern)

        self.qian_wan_yi_yuan_exception_check_pattern = re.compile(r'[k千仟w万萬亿]元[0-9]')
        self.money_num_string_pattern = re.compile(MONEY_NUM_STRING)
        self.money_string_pattern = re.compile(MONEY_CHAR_STRING)
        self.money_unit_pattern = re.compile(MONEY_SUFFIX_CASE_STRING)
        self.money_span_seg_pattern = re.compile('[-~—－～]+')

        # 此类表达虽然可按货币金额解析，但是文本中很大概率并非表示货币金额，故以大概率进行排除，
        # 并设参数 ret_all，即返回所有进行控制，默认为 False，即根据词典进行删除
        # 删除性正则
        # - 单纯包含 分、角、块，而无其它格式货币的
        # - 特殊词汇如 “多元” 等
        self.money_kuai_map_jiao_fen_pattern = re.compile(MONEY_KUAI_MAO_JIAO_FEN_STRING)
        self.non_money_string_list = {'多元', '十分', '百分', '万分'}

        self.print_exception = False

    def __call__(self, text, with_parsing=True, ret_all=False,
                 print_exception=False, use_jiojio=False):

        if self.parse_money is None:
            self._prepare()

        self.print_exception = print_exception

        candidates_list = self.extract_money_candidates(text)

        seg_offset_set = None

        money_entity_list = []
        for candidate in candidates_list:
            offset = [0, 0]
            bias = 0
            while candidate['offset'][0] + offset[1] < candidate['offset'][1]:
                # 此循环意在找出同一个 candidate 中包含的多个 money_entity

                true_string, result, offset = self.grid_search(
                    candidate['money_candidate'][bias:])

                if true_string is not None:

                    # rule 1: 判断字符串是否为大概率非货币金额语义
                    if (true_string in self.non_money_string_list) and (not ret_all):
                        bias += offset[1]
                        continue

                    # rule 2: 某些字符串本身可以理解为货币金额，但和上下文产生歧义
                    # 若金额实体的边界和分词边界产生冲突，则抛弃该实体。
                    if with_parsing:
                        money_entity_list.append(
                            {'text': true_string,
                             'offset': [candidate['offset'][0] + bias + offset[0],
                                        candidate['offset'][0] + bias + offset[1]],
                             'type': 'money',
                             'detail': result})
                    else:
                        money_entity_list.append(
                            {'text': true_string,
                             'offset': [candidate['offset'][0] + bias + offset[0],
                                        candidate['offset'][0] + bias + offset[1]],
                             'type': 'money'})
                    bias += offset[1]
                else:
                    break

        return money_entity_list

    def _filter(self, money_string):
        # 对字符串进行过滤，某些不符合规则的字符串直接跳过
        # rule 1: 清除边界的标点
        if money_string[0] in '，,' or money_string[-1] in '，,':
            return False

        # rule 2: 字符串为纯数值，则剔除，如 “12”
        if self.money_num_string_pattern.search(money_string):
            return False

        # rule 3: [千万亿]元 后一般不再添加数字再构成角分等信息，如：`359万元2`
        matched_res = self.qian_wan_yi_yuan_exception_check_pattern.search(money_string)
        if matched_res:
            return False

        # rule 4: 字符串中无货币单位，且无金额范围间隔符，则说明字符串有错误
        matched_res_1 = self.money_unit_pattern.search(money_string)
        matched_res_2 = self.money_span_seg_pattern.search(money_string)
        if matched_res_1 is None:
            if matched_res_2 is None:
                return False

            # 若有两个以上的间隔字符，说明字符串也是错误的。如“132017-04-09”
            span_seg_res = self.money_span_seg_pattern.findall(money_string)
            if len(span_seg_res) > 1:
                return False

            # 若仅有一个字符间隔，但无 k 或 w 字符样式，也是错误的。如 “12w~19w”
            if 'k' not in money_string and 'w' not in money_string:
                return False

        # rule 5: 字符串中仅仅有货币单位，而无货币数额，则说明字符串有误，如，“人民币”，无任何实值
        if matched_res_1:
            span_tuple = matched_res_1.span()
            if span_tuple[1] - span_tuple[0] == len(money_string):
                return False

        return True

    def _cleaning(self, money_string):
        # 对字符串进行清洗
        # 清洗空格字符串
        money_string = money_string.replace(' ', '')

        return money_string

    def grid_search(self, money_candidate):
        """ 全面搜索候选货币金额字符串，从长至短，较优 """
        length = len(money_candidate)
        for i in range(length):  # 控制总长，若想控制单字符的串也被返回考察，此时改为 length + 1
            for j in range(i):  # 控制偏移
                try:
                    offset = [j, length - i + j + 1]
                    sub_string = money_candidate[j: offset[1]]

                    # 对字符串进行过滤
                    if not self._filter(sub_string):
                        continue

                    # 对字符串进行清洗
                    clean_sub_string = self._cleaning(sub_string)

                    result = self.parse_money(clean_sub_string)

                    return sub_string, result, offset
                except (ValueError, Exception):
                    if self.print_exception:
                        print(traceback.format_exc())

                    continue

        return None, None, None

    def _grid_search_2(self, money_candidate):
        """ 全面搜索候选货币金额字符串，从前至后，从长至短 """
        # print(money_candidate)
        length = len(money_candidate)
        for i in range(length - 1):  # 控制起始点
            for j in range(length, i, -1):  # 控制终止点
                try:
                    offset = [i, j]
                    sub_string = money_candidate[i: j]
                    # print(sub_string)
                    # 处理假阳性。检查子串，对某些产生歧义的内容进行过滤。
                    # 原因在于，parse_money 会对某些不符合要求的字符串做正确解析.
                    if not MoneyExtractor._filter(sub_string):
                        continue

                    result = self.parse_money(sub_string, strict=True)

                    return sub_string, result, offset
                except (ValueError, Exception):
                    continue

        return None, None, None

    def extract_money_candidates(self, text):
        """ 获取所有的候选货币金额字符串，其中包含了货币金额

        但该正则范围较为宽泛，包含了并非货币金额的字符串。因此若遇到 bug，请提 issue 告知。
        """
        idx_count = 0
        text_length = len(text)
        money_candidates_list = []
        while idx_count < text_length:
            matched_res = self.money_string_pattern.search(text[idx_count:])

            if matched_res is not None:
                tmp_str = matched_res.group()
                if len(tmp_str) > 1:
                    if len(''.join(self.money_kuai_map_jiao_fen_pattern.findall(tmp_str))) == 1 and (
                            '元' not in tmp_str and '钱' not in tmp_str):
                        # 仅有一个 `分毛角块` 字符且无 `元钱` 字符
                        idx_count += matched_res.span()[1]
                        continue

                    money_candidates_list.append(
                        {'money_candidate': matched_res.group(),
                         'offset': [idx_count + matched_res.span()[0],
                                    idx_count + matched_res.span()[1]],
                         'context': text[max(0, idx_count - 5 + matched_res.span()[0]):
                                         min(text_length, idx_count + 5 + matched_res.span()[1])]}
                    )
                idx_count += matched_res.span()[1]
            else:
                break

        return money_candidates_list


def extract_money(question: str):
    try:
        money = None
        money_word_list = MoneyExtractor()(question)
        money_num_list = [MoneyParser()(text["text"]) for text in money_word_list]

        if len(money_num_list) > 0:
            money = str(int(float(money_num_list[0]["num"])))

        if money is None:
            pattern = re.compile(r"(?:充值|充|交|缴费|￥)\s*(\d{1,4})")
            extract_money = re.findall(pattern, question)
            if extract_money:
                money = extract_money[0]

        return money

    except Exception as e:
        ...


if __name__ == '__main__':
    text = '''海航亏损7000万港元出售香港公寓。12月12日，据《香港经济日报》报道，
        海航集团将持有的部分位于香港铜锣湾Yoo Residence大楼中的物业以2.6亿港元的价格出售，相对于去年入手时3.3亿港元的价格来看，
        海航此次出售该物业以公司股权转让的模式转售，亏损了7000多万港元。该物业包括一个顶层复式豪华公寓、1个分层物业及5个车位。
        报道称，两个月前，海航在市场上为该部分物业寻找买家，一度报价达到几千万美元。此外，海航在数月前将去年同时买下的一个地下连1楼的商铺
        以8650万港元的价格出售，买家为香港一家名为荣企的公司，较去年近1.2亿港元入手的价格亏损了约3350万港元。
        以此来看，海航投资Yoo Residence在一年内亏损逾1亿港元。今年以来，海航在香港连续出售其持有的地产类资产。
        2月份，海航集团把香港启德区6565号地块和6562号地块以159.59亿港元卖给了香港恒基兆业地产（00012.HK），股价为二十三块四毛钱。
        3月份，海航又把位于九龙启德第1L区1号地盘新九龙内地段第6564号以63.59亿港元的价格卖给了会德丰（00020.HK）。
        已在5个月前为其融到了50.47亿港元。除了出售地块之外，海航还卖掉了在香港金钟的一处办公室。3月21日，据香港当地媒体《明报》报道，
        海航已于今日出售位于香港金钟力宝中心的一处办公室，成交价为4000多万港元，折合单价为28000港元/平方英尺（折合243300元/平方米），
        较该物业的市场价值38000港元/平方英尺低了近两成。截至目前，海航在香港出售地产类物业已套现至少227亿港元。'''

    text = "交1000块"
    res = extract_money(text)
    print(res)
