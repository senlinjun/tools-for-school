from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import time, json, ctypes, os, math, re, urllib3

WIDTH = 300
WIDTH_WITHOUT_FRAME = WIDTH - 40
WEEKDAY = ["Mon.", "Tue.", "Wed.", "Thu.", "Fri.", "Sat.", "Sun."]


def getTodaysZero():
    """
    获取当天零点的时间戳
    """
    return (
        datetime.fromtimestamp(time.time())
        .replace(hour=0, minute=0, second=0)
        .timestamp()
    )


def drawTitle(main, title, font, config, y):
    """
    绘制标题
    如：每日课表
    """
    color = config["color"]
    length = font.getlength(title)
    main.text((int((WIDTH - length) / 2), y), title, fill=color, font=font)
    return 60  # 返回纵向(即y轴)占用空间


def drawSubTitle(main, title, font, config, y):
    """
    绘制副标题
    如：上午
    """
    color = config["color"]
    length = font.getlength(title)
    main.text((int((WIDTH - length) / 2), y), title, fill=color, font=font)


def drawLesson(main, head, head_font, content, content_font, highlight, config, y):
    """
    绘制课程
    如：|1| |  语文  |
    """
    color = config["color"]
    head_length = head_font.getlength(head)
    content_length = content_font.getlength(content)
    if highlight:
        main.rectangle((40, y, 80, y + 40), color)
        main.text(
            (40 + int((40 - head_length) / 2), y + 5),
            head,
            fill=(255, 255, 255),
            font=head_font,
        )
    else:
        main.text(
            (40 + int((40 - head_length) / 2), y + 5), head, fill=color, font=head_font
        )
    main.rectangle((90, y, WIDTH_WITHOUT_FRAME, y + 40), color)
    main.text(
        (90 + int((170 - content_length) / 2), y + 5),
        content,
        fill=(255, 255, 255),
        font=content_font,
    )


def getPartLength(lessons):
    """
    计算每一个part所占的空间
    """
    return 55 * (len(lessons) + 1)


def drawPart(main, sub_title, sub_title_font, lessons: list, config, y):
    """
    绘制一个part
    """
    color = config["color"]
    drawSubTitle(main, sub_title, sub_title_font, config, y)
    for i in range(len(lessons)):
        lesson = lessons[i]
        head, head_font, content, content_font, highlight = lesson
        drawLesson(
            main,
            head,
            head_font,
            content,
            content_font,
            highlight,
            config,
            y + 55 + i * 55,
        )
    return 55 * (len(lessons) + 1)


def getConfig():
    """
    获取配置文件
    """
    with open("./lesson_table/config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    config["color"] = tuple(config["color"])
    return config


def setConfig(config):
    """
    设置配置文件
    """
    with open("./lesson_table/config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=1)


def getWeek(config):
    """
    获取当前为开学第几周
    """
    return math.ceil((getTodaysZero() - config["term_beginning"]) / 604800)


def getWeekday():
    """
    获取今天星期几
    """
    return datetime.fromtimestamp(time.time()).weekday()


def getTodaysLesson(config):
    """
    获取当天课表
    """
    weekday = getWeekday()
    odd_even_week = int(getWeek(config)) % 2

    words = config["lang"]
    todays_lesson_table = config["lesson_table"][weekday]
    lessons = {}

    # 处理parts
    parts = list(config["parts_in_order"])
    for part in config["parts_in_order"]:
        if part not in todays_lesson_table.keys():
            parts.remove(part)
    lessons["parts_in_order"] = [words[part] for part in parts]

    lessons["lessons"] = {}  # 处理课程
    for part in todays_lesson_table:
        lessons["lessons"][words[part]] = []
        lessons["lessons"][words[part]].append(todays_lesson_table[part][0])
        for i in range(1, len(todays_lesson_table[part])):
            lesson = todays_lesson_table[part][i]
            beginning, ending, head, content = lesson
            if "|" in content:  # 分单双周
                odd_even = content = content.split("|")
                if odd_even_week == 0:  # 双周
                    content = odd_even[1]
                else:  # 单周
                    content = odd_even[0]
            lessons["lessons"][words[part]].append(
                (beginning, ending, words[head], words[content])
            )

    return lessons


def drawFormatText(main, font, text, args, config, x1, y, align=0, x2=0):
    """
    格式化并绘制一行文字
    """
    text = text % args  # 格式化字符串

    # 分离普通/高亮文字
    normal_blocks = []
    highlight_blocks = []
    while True:
        result = re.search("\[(.+?)\]", text)
        if result is None:
            break
        highlight_block = result.group()
        index_begin = text.index(highlight_block)
        index_end = index_begin + len(highlight_block)
        normal_blocks.append(text[:index_begin])
        highlight_blocks.append(highlight_block[1:-1])
        text = text[index_end:]
    normal_blocks.append(text)  # 加上最后一段

    # 预先计算横向(即x轴)占用空间
    length_cnt = 0
    for block in normal_blocks:
        length_cnt += font.getlength(block)
    for block in highlight_blocks:
        length_cnt += font.getlength(block) + 10

    if align == 0:  # 计算居左/居中/居右时的绘制起点
        x = x1 + 5
    elif align == 1:
        x = x1 + int((x2 - x1 - length_cnt) / 2)
    elif align == 2:
        x = x2 - length_cnt - 5

    for i in range(len(highlight_blocks)):  # 绘制文字
        normal_block = normal_blocks[i]  # 普通文字
        highlight_block = highlight_blocks[i]
        main.text((x, y + 5), normal_block, fill=config["color"], font=font)
        x += font.getlength(normal_block)

        length = font.getlength(highlight_block)  # 高亮文字
        main.rectangle((x, y, x + length + 10, y + 40), config["color"])
        main.text((x + 5, y + 5), highlight_block, fill=(255, 255, 255), font=font)
        x += length + 10

    main.text(
        (x, y + 5), normal_blocks[-1], fill=config["color"], font=font
    )  # 加上最后一段

    return 55  # 返回纵向(即y轴)占用空间


def setWallpaper(path):
    """
    设置壁纸
    """
    ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 0)


def generateWallpaper(lesson_img, bg_img, width):
    """
    生成壁纸
    """
    bl = width / lesson_img.size[0]
    lesson_img.thumbnail((int(lesson_img.size[0] * bl), int(lesson_img.size[1] * bl)))
    if lesson_img.size[1] >= bg_img.size[1] - 100:
        bl = (bg_img.size[1] - 100) / lesson_img.size[1]
        lesson_img.thumbnail(
            (int(lesson_img.size[0] * bl), int(lesson_img.size[1] * bl))
        )

    w, h = lesson_img.size
    bw, bh = bg_img.size
    x = bw - 50 - w
    y = int((bh - h) / 2)

    for i in range(w):
        for j in range(h):
            color = lesson_img.getpixel((i, j))
            bg_img.putpixel((i + x, j + y), color)
    bg_img.save("./lesson_table/tmp.png")


def getHolidays():
    """
    获取节假日
    """
    if "holidays" not in os.listdir("./lesson_table"):
        with open("./lesson_table/holidays", "w") as f:
            json.dump({"update_time": 0, "holiday_data": {}, "weekend_data": {}}, f)

    with open("./lesson_table/holidays", "r") as f:
        data = json.load(f)
    if (
        time.time() - data["update_time"] > 2592000
    ):  # 距离上一次更新节假日文件过了一个月
        year = datetime.now().year
        try:
            http = urllib3.PoolManager()
            url = f"https://api.jiejiariapi.com/v1/holidays/{year}"
            response = http.request("GET", url)
            holiday_data = json.loads(response.data.decode("utf-8"))
            url = f"https://api.jiejiariapi.com/v1/weekends/{year}"
            response = http.request("GET", url)
            weekend_data = json.loads(response.data.decode("utf-8"))
            data["update_time"] = time.time()
            data["holiday_data"] = holiday_data
            data["weekend_data"] = weekend_data
            with open("./lesson_table/holidays", "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(e)
            return {"update_time": 0, "holiday_data": {}, "weekend_data": {}}

    return data


def main():
    config = getConfig()
    lessons = getTodaysLesson(config)
    zero_hour = getTodaysZero()
    holidays = getHolidays()

    title = ImageFont.truetype(f'./lesson_table/{config["font"]}', 40)
    content = ImageFont.truetype(f'./lesson_table/{config["font"]}', 30)
    mini_content = ImageFont.truetype(f'./lesson_table/{config["font"]}', 25)

    last_table = []
    table_for_draw = {}
    remove_parts = []
    for part in lessons["parts_in_order"]:
        part_lesson = lessons["lessons"][part]
        t = time.time() - zero_hour
        if t < part_lesson[0][0] or t > part_lesson[0][1]:
            remove_parts.append(part)
            continue
        part_draw = []
        for i in range(1, len(part_lesson)):
            highlight = False
            t = time.time() - zero_hour
            if t >= part_lesson[i][0] and t <= part_lesson[i][1]:  # 高亮正在进行的课程
                highlight = True
            part_draw.append((part_lesson[i][2], part_lesson[i][3], highlight))
        table_for_draw[part] = part_draw
    for part in remove_parts:
        lessons["parts_in_order"].remove(part)
    # 计算画布大小
    y = 90
    lesson_y = 90
    event_y = 90
    # 课程显示的画布大小
    for part in table_for_draw:
        tmp = getPartLength(table_for_draw[part])
        y += tmp
        event_y += tmp
        lesson_y += tmp
    # 倒计时显示的画布大小
    # 获取倒计时并删除已过期的倒计时
    remove_event = []
    for event in config["event"]:
        days = int((config["event"][event][0] - zero_hour) / 86400)
        if days < 0:
            remove_event.append(event)
    for event in remove_event:
        config["event"].pop(event)
        setConfig(config)
    if len(config["event"]) > 0:
        x = 20 + len(config["event"]) * (55 * 2)
        y += x
        event_y += x
    # 日期显示的画布大小
    y += 15  # 间距
    y += 55  # 日期所占空间
    if not "last" in os.listdir("./lesson_table"):
        with open("./lesson_table/last", "w") as f:
            pass
    with open("./lesson_table/last", "r") as f:
        last_table = f.read()
    if json.dumps(table_for_draw) == last_table:  # 无需更新课程表
        return

    with open("./lesson_table/last", "w") as f:
        json.dump(table_for_draw, f)

    # 编辑图片
    img = Image.new("RGB", (WIDTH, y + 30), config["color"])
    main = ImageDraw.Draw(img)
    main.rectangle((20, 20, 280, lesson_y + 10), (255, 255, 255))
    main.rectangle((20, lesson_y + 20, 280, event_y + 10), (255, 255, 255))
    main.rectangle((20, event_y + 20, 280, y + 10), (255, 255, 255))
    y = 30

    # 绘制标题
    y += drawTitle(main, config["title"], title, config, y)

    # 绘制课程表
    for part in lessons["parts_in_order"]:
        table_with_font = []
        for lesson in table_for_draw[part]:
            head, content_text, highlight = lesson
            table_with_font.append(
                (head, mini_content, content_text, content, highlight)
            )
        y += drawPart(main, part, title, table_with_font, config, y)  # 绘制一个part

    y += 30  # 间距

    # 绘制倒计时
    for event in config["event"]:
        days = int((config["event"][event][0] - zero_hour) / 86400)
        if config["event"][event][1]:  # 忽略节假日
            for date in holidays["holiday_data"]:
                datetime_obj = datetime.strptime(date, "%Y-%m-%d")
                timestamp = datetime_obj.timestamp()
                if (
                    timestamp >= zero_hour
                    and timestamp < config["event"][event][0]
                    and holidays["holiday_data"][date]["isOffDay"]
                ):
                    days -= 1
        if config["event"][event][2]:  # 忽略周末
            for date in holidays["weekend_data"]:
                datetime_obj = datetime.strptime(date, "%Y-%m-%d")
                timestamp = datetime_obj.timestamp()
                if timestamp >= zero_hour and timestamp < config["event"][event][0]:
                    days -= 1
        y += drawFormatText(
            main, content, config["lang"]["show_event_1"], event, config, 20, y
        )
        y += drawFormatText(
            main,
            content,
            config["lang"]["show_event_2"],
            str(days),
            config,
            20,
            y,
            2,
            WIDTH_WITHOUT_FRAME,
        )

    y += 20  # 间距
    y += drawFormatText(
        main,
        mini_content,
        config["lang"]["show_date"],
        (str(getWeek(config)), config["lang"][WEEKDAY[getWeekday()]]),
        config,
        20,
        y,
        1,
        WIDTH_WITHOUT_FRAME,
    )

    bg_img = Image.open("./lesson_table/background.png")
    generateWallpaper(img, bg_img, config["width"])
    setWallpaper(f"{os.getcwd()}\\lesson_table\\tmp.png")
