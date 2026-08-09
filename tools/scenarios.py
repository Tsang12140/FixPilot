"""
FixPilot 故障真相数据集（陪练 AI 据此动态应答，不存对话剧本）

每个场景存"完整故障情况"，分两块：
  - facts: 模拟用户已知的事实（陪练 AI 据此回答 FixPilot 的提问）
      * initial_complaint  第一句模糊主诉
      * symptoms           能被问出来的症状细节
      * hardware           硬件配置（该人设能说清的部分）
      * timeline           事发前经过
      * prior_attempts     已经试过的操作
      * capabilities       能力/限制（不敢拆机等）
      * action_outcomes    FixPilot 让你做某操作后你会看到的结果（含 solves 标记）
      * images             能提供的图片 + 何时发
  - grading: 评分点（陪练 AI 不知道，测试引擎用来判 FixPilot 是否查对方向）
      * root_cause         真实根因
      * solution           真实修复
      * key_evidence       关键证据关键词
      * stop_when          达成判定（FixPilot 给出该方向判断即算查对）

人设只影响"怎么说"，不改变事实本身。内部测试分组使用 A/B/C：
  A = 可以直接讲重点（后端值 advanced）
  B = 会折腾一点（后端值 intermediate）
  C = 需要讲细（后端值 beginner）

这些代号仅供测试、报告和团队沟通使用，绝不作为面向用户的称呼。
"""

# ---------- 人设定义 ----------
# tech_level 对应 FixPilot 后端的 LEVEL_POLICIES；style 对应 STYLE_POLICIES
PERSONAS = {
    "A": {
        "label": "A级（可以直接讲重点）",
        "tech_level": "advanced",
        "style": "roast",
        # 陪练 AI 的表达指引（只影响措辞，不改变事实）
        "tutor_style": (
            "你是比较懂电脑的用户。术语精准，能直接报错误码全名、型号、温度、电压；"
            "会主动说自己排查过的项和结果（如 memtest 跑过几轮）；"
            "毒舌模式可接 FixPilot 的梗、回怪一两句，但不影响推进排查。"
            "回复像真人聊天，短句，可带点锋芒，不分点不罗列，不用 emoji 和圆点符号。"
        ),
    },
    "B": {
        "label": "B级（会折腾一点）",
        "tech_level": "intermediate",
        "style": "normal",
        "tutor_style": (
            "你是会折腾一点电脑的用户。会说一些术语但不一定精准；能做基本操作（任务管理器、设备管理器、安全模式、查型号）；"
            "会主动说'我之前试过 XX 不管用'；遇到没把握的步骤会问，但不至于完全听不懂。"
            "回复像真人聊天，自然短句，不分点不罗列，不用 emoji 和圆点符号。"
        ),
    },
    "C": {
        "label": "C级（需要讲细）",
        "tech_level": "beginner",
        "style": "normal",
        "tutor_style": (
            "你是不太懂电脑的普通用户。说话口语化、模糊、会用'那个''就是''啥'之类口头词；"
            "不懂术语，被问到型号/参数时尽量说'我不懂这些''没注意'；"
            "容易慌、会问'会不会坏''要不要紧'；不敢拆机，需要被一步步带着做。"
            "回复像真人聊天，短句，不分点不罗列，不用 emoji 和圆点符号。"
        ),
    },
}

SCENARIOS = [
    # ==================== C 级场景：需要讲细 ====================
    {
        "id": "C01",
        "persona": "C",
        "title": "内存条松动导致蓝屏",
        "facts": {
            "initial_complaint": "电脑突然蓝屏了，屏幕变蓝写了一堆英文，吓死我了",
            "symptoms": [
                "屏幕变蓝，上面有一堆英文和一个二维码",
                "进度条走到 100% 就不动了，得强制关机",
                "之前一直好好的，就刚才开始的",
            ],
            "hardware": {
                "内存": "不太清楚，是个长条，上面写着 kingston",
                "主板": "不知道",
                "电源": "不知道",
                "CPU": "不知道",
            },
            "timeline": [
                "半小时前我搬了一下电脑桌，主机碰了一下桌子腿",
                "之后开机就蓝屏了",
            ],
            "prior_attempts": ["重启过一次，还是蓝屏"],
            "capabilities": "完全不懂拆机，不敢碰里面的零件，需要被一步步带着做；不知道内存条长什么样",
            "action_outcomes": [
                {"trigger": "拔下内存条", "result": "拔下来了，上面金色的那排针脚有点发黑，像氧化了"},
                {"trigger": "清理金手指后插回", "result": "用橡皮擦了擦，插回去听到咔嗒一声卡好了，开机正常进系统，没再蓝屏", "solves": True},
                {"trigger": "重新插内存", "result": "插紧了，开机好了"},
            ],
            "images": [
                {
                    "path": "images/bsod_0x7e.jpg",
                    "shows": "蓝屏画面，错误代码 STOP 0x0000007E",
                    "send_when": "FixPilot 问到错误代码 / 截图 / 拍照时发",
                    "send_when_asked_terms": ["蓝屏", "错误代码", "画面", "截图", "拍照", "发图"],
                    "must_send_by_round": 3
                },
            ],
        },
        "grading": {
            "root_cause": "内存条金手指接触不良（搬动后松动 + 轻微氧化）",
            "solution": "断电拔下内存条，橡皮擦清理金手指，重新插紧",
            "key_evidence": ["搬动", "金手指", "氧化", "拔插", "内存"],
            "direction_evidence_groups": [["金手指", "氧化", "内存接触", "内存条松"]],
            "stop_when": "FixPilot 给出内存条松动/金手指方向的判断并指导拔插清理",
        },
    },
    {
        "id": "C02",
        "persona": "C",
        "title": "电脑卡顿，浏览器吃内存",
        "facts": {
            "initial_complaint": "电脑好卡啊，点什么都半天才反应，急死人",
            "symptoms": [
                "这两天开始的，以前还好好的",
                "就开了浏览器和微信，别的没开什么",
                "有时候鼠标动一下都要等一会",
            ],
            "hardware": {"内存": "好像 8G", "CPU": "不知道", "系统": "Windows 10"},
            "timeline": ["前两天开始卡的，没装过新东西"],
            "prior_attempts": ["重启过，刚重启好一会儿，过一阵又卡"],
            "capabilities": "不知道任务管理器怎么打开，需要被教；看不懂里面的英文进程名",
            "action_outcomes": [
                {"trigger": "打开任务管理器", "result": "打开了，看到好多行，不知道哪个是内存"},
                {"trigger": "看内存占用", "result": "有个 chrome.exe 占了好大一截，颜色是红的/深的"},
                {"trigger": "结束 chrome 进程", "result": "关掉了，现在明显快多了，鼠标一下就动了"},
                {"trigger": "重启", "result": "重启完很流畅", "solves": True},
            ],
            "images": [
                {
                    "path": "images/task_manager_high_mem.jpg",
                    "shows": "任务管理器，chrome.exe 内存占用很高",
                    "send_when": "FixPilot 让你看任务管理器内存占用时发",
                    "send_when_asked_terms": ["任务管理器", "内存占用", "截图", "发图"],
                    "must_send_by_round": 3
                },
            ],
        },
        "grading": {
            "root_cause": "浏览器进程内存占用过高导致整体卡顿",
            "solution": "任务管理器结束高占用进程，必要时重启",
            "key_evidence": ["任务管理器", "chrome", "内存", "占用", "结束进程"],
            "direction_evidence_groups": [["chrome", "浏览器"], ["内存占用", "高占用", "结束进程"]],
            "stop_when": "FixPilot 指引打开任务管理器并定位到高内存进程",
        },
    },
    {
        "id": "C03",
        "persona": "C",
        "title": "开机没反应，插座没电",
        "facts": {
            "initial_complaint": "电脑开不了机了！按了开机键一点反应都没有！",
            "symptoms": [
                "按开机键，什么反应都没有",
                "主机灯不亮，风扇也不转，一点声音都没有",
                "显示器是好的，灯亮着",
            ],
            "hardware": {"电源": "不知道", "主机": "就一个黑盒子"},
            "timeline": ["昨天还能用，今天早上就不行了", "昨晚下过雨"],
            "prior_attempts": ["按了好几次开机键都没用"],
            "capabilities": "完全不懂，能做的是看灯、拔插头、换插座；不敢拆主机",
            "action_outcomes": [
                {"trigger": "检查电源线插紧", "result": "电源线插着的，我拔了重新插紧了，还是不行"},
                {"trigger": "换插座", "result": "换到另一个插座上，灯亮了！风扇转了！", "solves": True},
            ],
            "images": [],
        },
        "grading": {
            "root_cause": "原插座无电（跳闸/接触不良）",
            "solution": "更换供电插座",
            "key_evidence": ["插座", "电源线", "换", "供电"],
            "direction_evidence_groups": [["插座", "供电"]],
            "stop_when": "FixPilot 指引检查供电/插座/电源线方向",
        },
    },

    # ==================== B 级场景：会折腾一点 ====================
    {
        "id": "B01",
        "persona": "B",
        "title": "蓝屏 0x0000007E，显卡驱动冲突",
        "facts": {
            "initial_complaint": "电脑蓝屏了，错误代码 STOP: 0x0000007E",
            "symptoms": [
                "能进安全模式",
                "设备管理器里显卡那栏有个黄色感叹号",
                "前两天用驱动精灵更新了显卡驱动",
            ],
            "hardware": {
                "显卡": "NVIDIA GTX 1660",
                "主板": "微星 B460",
                "系统": "Windows 10 64位",
            },
            "timeline": ["前两天用驱动精灵装了新显卡驱动", "之后偶尔蓝屏，今天蓝得厉害"],
            "prior_attempts": ["重启过几次，有时能进系统有时蓝"],
            "capabilities": "会进安全模式、会用设备管理器、会卸载驱动；不会刷 BIOS、不会拆硬件",
            "action_outcomes": [
                {"trigger": "卸载显卡驱动", "result": "在设备管理器卸载了显卡驱动，勾了删除驱动文件"},
                {"trigger": "重启", "result": "重启后没蓝屏，进系统了，显卡先用基础驱动", "solves": True},
                {"trigger": "装回官方驱动", "result": "去官网下了对应驱动，装上正常了"},
            ],
            "images": [
                {
                    "path": "images/device_manager_yellow.jpg",
                    "shows": "设备管理器，显卡项有黄色感叹号",
                    "send_when": "FixPilot 让看设备管理器状态时发",
                    "send_when_asked_terms": ["设备管理器", "状态", "截图", "发图"],
                    "must_send_by_round": 3
                },
            ],
        },
        "grading": {
            "root_cause": "第三方工具更新显卡驱动导致驱动冲突",
            "solution": "安全模式卸载问题驱动，重启后装官方驱动",
            "key_evidence": ["驱动", "显卡", "驱动精灵", "卸载", "安全模式", "回滚"],
            "direction_evidence_groups": [["驱动精灵", "显卡驱动", "安全模式", "回滚驱动"]],
            "stop_when": "FixPilot 判断驱动方向并指引安全模式卸载/回滚",
        },
    },
    {
        "id": "B02",
        "persona": "B",
        "title": "休眠后无法唤醒黑屏",
        "facts": {
            "initial_complaint": "电脑休眠后唤不醒，屏幕黑的，主机灯还亮着",
            "symptoms": [
                "睡眠后按键盘鼠标没反应，屏幕一直黑",
                "主机电源灯亮着，但硬盘灯不闪",
                "长按电源强制关机后能正常进系统",
                "进系统后一切正常，就是不能正常唤醒",
            ],
            "hardware": {"主板": "华硕 B550M", "显卡": "RTX 3060", "系统": "Windows 11"},
            "timeline": ["大概一两周前开始的，以前没事"],
            "prior_attempts": ["更新过显卡驱动，是最新的", "电源选项看了，设置的是睡眠"],
            "capabilities": "会改电源选项、会关快速启动、能查 BIOS 版本但不太敢刷",
            "action_outcomes": [
                {"trigger": "关快速启动", "result": "在电源选项里关掉了快速启动"},
                {"trigger": "测试睡眠", "result": "关了快速启动后试了几天，没再出现唤不醒", "solves": True},
            ],
            "images": [],
        },
        "grading": {
            "root_cause": "Windows 快速启动与睡眠/驱动兼容性问题",
            "solution": "关闭快速启动",
            "key_evidence": ["快速启动", "睡眠", "电源选项", "唤醒"],
            "direction_evidence_groups": [["快速启动", "关闭快速启动"]],
            "stop_when": "FixPilot 指向快速启动/电源选项方向",
        },
    },
    {
        "id": "B03",
        "persona": "B",
        "title": "应用程序无法启动 0xc0000005",
        "facts": {
            "initial_complaint": "打开一个软件弹出来一个错误框，写了一串数字 0xc0000005",
            "symptoms": [
                "双击软件图标就弹错误框",
                "错误提示是 应用程序无法正常启动 0xc0000005",
                "这个软件之前能用的，最近不知道怎么了",
            ],
            "hardware": {"系统": "Windows 10"},
            "timeline": ["前两天系统更新过一次"],
            "prior_attempts": ["重装过这个软件，还是不行"],
            "capabilities": "会用兼容性疑难解答、会以管理员身份运行；不会改注册表",
            "action_outcomes": [
                {"trigger": "兼容性运行", "result": "右键属性兼容性，勾了以管理员身份运行，还是弹错"},
                {"trigger": "兼容性疑难解答", "result": "跑了疑难解答，选了上一个能用的 Windows 版本，应用后能打开了", "solves": True},
            ],
            "images": [
                {
                    "path": "images/error_0xc0000005.jpg",
                    "shows": "错误对话框，应用程序无法正常启动 0xc0000005",
                    "send_when": "FixPilot 问错误截图/拍照时发",
                    "send_when_asked_terms": ["错误", "截图", "拍照", "发图"],
                    "must_send_by_round": 3
                },
            ],
        },
        "grading": {
            "root_cause": "系统更新后兼容性问题",
            "solution": "兼容性模式运行",
            "key_evidence": ["兼容性", "0xc0000005", "管理员", "疑难解答"],
            "direction_evidence_groups": [["兼容性", "兼容模式", "疑难解答"]],
            "stop_when": "FixPilot 指向兼容性/权限方向",
        },
    },

    # ==================== A 级场景：可以直接讲重点 ====================
    {
        "id": "A01",
        "persona": "A",
        "title": "蓝屏 0x0000007E，内存金手指氧化",
        "facts": {
            "initial_complaint": "蓝屏了，STOP 0x0000007E，PAGE_FAULT_IN_NONPAGED_AREA",
            "symptoms": [
                "蓝屏码不固定，主要是 0x7E，偶尔 0x50",
                "前两天搬过机箱",
                "间歇性蓝，有时能跑几小时，有时开机就蓝",
            ],
            "hardware": {
                "内存": "金士顿 DDR4 3200 16G x2",
                "主板": "华硕 B550M",
                "CPU": "Ryzen 5 5600",
                "电源": "海韵 Focus GX-650",
            },
            "timeline": ["前两天搬机箱清灰，之后开始蓝屏"],
            "prior_attempts": [
                "memtest86 跑了 2 轮没报错（但接触不良时偶尔过）",
                "系统日志看了，全是 bugcheck 0x7E",
            ],
            "capabilities": "会拆机、会用万用表、会跑 memtest86、会看事件查看器；能自己换插槽测",
            "action_outcomes": [
                {"trigger": "拔内存看金手指", "result": "拔下来了，金手指有明显氧化发黑，其中一根更严重"},
                {"trigger": "橡皮擦清理", "result": "橡皮擦干净了，换了远端插槽，吹了灰，插回卡紧"},
                {"trigger": "开机测", "result": "开机正常，跑了半小时 memtest86 全过，没再蓝", "solves": True},
            ],
            "images": [
                {
                    "path": "images/bsod_0x7e.jpg",
                    "shows": "蓝屏 STOP 0x0000007E PAGE_FAULT_IN_NONPAGED_AREA",
                    "send_when": "FixPilot 问蓝屏画面/截图时发",
                    "send_when_asked_terms": ["蓝屏", "错误代码", "画面", "截图", "拍照", "发图"],
                    "must_send_by_round": 3
                },
            ],
        },
        "grading": {
            "root_cause": "搬机箱后内存金手指接触不良 + 氧化",
            "solution": "拔下内存，橡皮擦清理金手指，换插槽重新插紧",
            "key_evidence": ["金手指", "氧化", "拔插", "内存", "接触不良"],
            "direction_evidence_groups": [["金手指", "氧化", "内存接触", "接触不良"]],
            "stop_when": "FixPilot 判断内存接触/金手指方向并指引拔插清理",
        },
    },
    {
        "id": "A02",
        "persona": "A",
        "title": "高频蓝屏，电源 12V 老化",
        "facts": {
            "initial_complaint": "频繁蓝屏，错误码不固定，0x7E、0x124、0x50 都有",
            "symptoms": [
                "蓝屏码不固定，以 0x124（硬件错误）居多",
                "高负载时更容易蓝（打游戏、跑压力测试）",
                "有时黑屏重启，不蓝屏",
            ],
            "hardware": {
                "CPU": "Ryzen 7 5800X",
                "主板": "微星 X570",
                "内存": "芝奇 DDR4 3600 16G x2",
                "电源": "长城 550W 额定，用了 5 年多",
                "显卡": "RTX 3070",
            },
            "timeline": ["最近一两个月越来越频繁，电源用了 5 年了"],
            "prior_attempts": [
                "memtest86 跑 4 轮全过，内存排除",
                "CPU 待机 35 度，满载 65 度，温度正常",
                "系统重装过一次，没用",
            ],
            "capabilities": "能拆机、有万用表、能换电源测、能跑压力测试",
            "action_outcomes": [
                {"trigger": "测电源 12V", "result": "万用表测 12V，待机 11.6V，满载掉到 11.2V，偏低"},
                {"trigger": "换电源", "result": "换了个新电源（海韵 750W），跑了一周压力测试和游戏都没再蓝", "solves": True},
            ],
            "images": [],
        },
        "grading": {
            "root_cause": "电源老化导致 12V 输出不稳（满载掉压）",
            "solution": "更换电源",
            "key_evidence": ["电源", "12V", "老化", "满载", "掉压", "瓦数"],
            "direction_evidence_groups": [["12v", "掉压", "电源老化"]],
            "stop_when": "FixPilot 在排除内存/温度后指向电源方向",
        },
    },
    {
        "id": "A03",
        "persona": "A",
        "title": "设备管理器黄三角，网卡 PCIe 接触",
        "facts": {
            "initial_complaint": "设备管理器里网卡有个黄色感叹号，上不了网",
            "symptoms": [
                "设备管理器网卡项黄三角，错误代码 10 或 43",
                "完全连不上网，网线插着没反应",
                "设备状态说 该设备无法启动",
            ],
            "hardware": {
                "网卡": "Realtek PCIe 千兆",
                "主板": "华硕 Z690",
                "系统": "Windows 11",
            },
            "timeline": ["前两天搬过机箱"],
            "prior_attempts": [
                "卸载重装驱动，重启后还是黄三角",
                "官网下了最新 Realtek 驱动，装上没用",
                "进 BIOS 看，PCIe 插槽是开启的",
            ],
            "capabilities": "能拆机换插槽、会进 BIOS、会装驱动；有备用 PCIe 网卡",
            "action_outcomes": [
                {"trigger": "换 PCIe 插槽", "result": "拔下来换到另一个插槽，重新装驱动，黄三角没了，能上网了", "solves": True},
            ],
            "images": [
                {
                    "path": "images/device_manager_yellow.jpg",
                    "shows": "设备管理器，网卡项黄色感叹号",
                    "send_when": "FixPilot 问设备管理器状态时发",
                    "send_when_asked_terms": ["设备管理器", "状态", "截图", "发图"],
                    "must_send_by_round": 3
                },
            ],
        },
        "grading": {
            "root_cause": "搬机箱后网卡 PCIe 接触不良",
            "solution": "换 PCIe 插槽重新插紧并重装驱动",
            "key_evidence": ["PCIe", "插槽", "接触", "网卡", "换"],
            "direction_evidence_groups": [["pcie", "插槽", "接触不良"]],
            "stop_when": "FixPilot 在驱动方向无效后指向硬件/插槽方向",
        },
    },
]
