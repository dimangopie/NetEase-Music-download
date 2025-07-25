import gradio as gr
import json
import os
import urllib.parse
from hashlib import md5
from random import randrange
import requests
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from CookieManager import CookieManager
from urllib.parse import urlparse
import shutil
from pathlib import Path


def HexDigest(data):
    return "".join([hex(d)[2:].zfill(2) for d in data])

def HashDigest(text):
    HASH = md5(text.encode("utf-8"))
    return HASH.digest()

def HashHexDigest(text):
    return HexDigest(HashDigest(text))

def parse_cookie(text: str):
    cookie_ = [item.strip().split('=', 1) for item in text.strip().split(';') if item]
    cookie_ = {k.strip(): v.strip() for k, v in cookie_}
    return cookie_

def ids(ids):
    if '163cn.tv' in ids:
        response = requests.get(ids, allow_redirects=False)
        ids = response.headers.get('Location')
    if 'music.163.com' in ids:
        index = ids.find('id=') + 3
        ids = ids[index:].split('&')[0]
    return ids

def size(value):
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = 1024.0
    for i in range(len(units)):
        if (value / size) < 1:
            return "%.2f%s" % (value, units[i])
        value = value / size
    return value

def music_level1(value):
    if value == 'standard':
        return "标准音质"
    elif value == 'exhigh':
        return "极高音质"
    elif value == 'lossless':
        return "无损音质"
    elif value == 'hires':
        return "Hires音质"
    elif value == 'sky':
        return "沉浸环绕声"
    elif value == 'jyeffect':
        return "高清环绕声"
    elif value == 'jymaster':
        return "超清母带"
    else:
        return "未知音质"

def music_level2(value):
    if value == '标准音质':
        return 'standard'
    elif value == '极高音质':
        return 'exhigh'
    elif value == '无损音质':
        return 'lossless'
    elif value == 'Hires音质':
        return 'hires'
    elif value == '沉浸环绕声':
        return 'sky'
    elif value == '高清环绕声':
        return 'jyeffect'
    elif value == '超清母带':
        return 'jymaster'
    else:
        return "未知音质"

def post(url, params, cookie):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36 Chrome/91.0.4472.164 NeteaseMusicDesktop/2.10.2.200154',
        'Referer': '',
    }
    cookies = {
        "os": "pc",
        "appver": "",
        "osver": "",
        "deviceId": "pyncm!"
    }
    cookies.update(cookie)
    response = requests.post(url, headers=headers, cookies=cookies, data={"params": params})
    return response.text

def read_cookie():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cookie_file = os.path.join(script_dir, 'cookie.txt')
    with open(cookie_file, 'r') as f:
        cookie_contents = f.read()
    return cookie_contents

def get_file_extension(url):
    # 解析URL
    parsed_url = urlparse(url)
    # 提取路径部分
    path = parsed_url.path
    # 从路径中提取文件名
    file_name = os.path.basename(path)
    # 获取文件扩展名
    _, file_extension = os.path.splitext(file_name)
    return file_extension

def process_song_v1(url, level):
    if not url:
        return '错误: 必须提供url 参数', None
    if level is None:
        return '错误: level参数为空', None

    level = music_level2(level)
    jsondata = url
    cookies = parse_cookie(read_cookie())
    url = "https://interface3.music.163.com/eapi/song/enhance/player/url/v1"
    AES_KEY = b"e82ckenh8dichen8"
    config = {
        "os": "pc",
        "appver": "",
        "osver": "",
        "deviceId": "pyncm!",
        "requestId": str(randrange(20000000, 30000000))
    }
    payload = {
        'ids': [ids(jsondata)],
        'level': level,
        'encodeType': 'flac',
        'header': json.dumps(config),
    }
    if level == 'sky':
        payload['immerseType'] = 'c51'
    url2 = urllib.parse.urlparse(url).path.replace("/eapi/", "/api/")
    digest = HashHexDigest(f"nobody{url2}use{json.dumps(payload)}md5forencrypt")
    params = f"{url2}-36cd479b6b5-{json.dumps(payload)}-36cd479b6b5-{digest}"
    padder = padding.PKCS7(algorithms.AES(AES_KEY).block_size).padder()
    padded_data = padder.update(params.encode()) + padder.finalize()
    cipher = Cipher(algorithms.AES(AES_KEY), modes.ECB())
    encryptor = cipher.encryptor()
    enc = encryptor.update(padded_data) + encryptor.finalize()
    params = HexDigest(enc)
    response = post(url, params, cookies)
    if "参数错误" in response:
        return "参数错误！", None

    jseg = json.loads(response)
    #歌曲信息接口
    song_names = "https://interface3.music.163.com/api/v3/song/detail"
    song_data = {'c': json.dumps([{"id":jseg['data'][0]['id'],"v":0}])}
    resp = requests.post(url=song_names, data=song_data)
    jse = json.loads(resp.text)
    #歌词接口
    lyric_names = "https://interface3.music.163.com/api/song/lyric"
    lyric_data = {'id' : jseg['data'][0]['id'],'cp' : 'false','tv' : '0','lv' : '0','rv' : '0','kv' : '0','yv' : '0','ytv' : '0','yrv' : '0'}
    lyricresp = requests.post(url=lyric_names, data=lyric_data, cookies=cookies)
    lyricjse = json.loads(lyricresp.text)

    if jseg['data'][0]['url'] is not None:
        if jse['songs']:
            song_url = jseg['data'][0]['url']
            song_name = jse['songs'][0]['name']
            song_picUrl = jse['songs'][0]['al']['picUrl']
            song_alname = jse['songs'][0]['al']['name']
            artist_names = []
            for song in jse['songs']:
                ar_list = song['ar']
                if len(ar_list) > 0:
                    artist_names.append('/'.join(ar['name'] for ar in ar_list))
                song_arname = ', '.join(artist_names)
            response = requests.get(song_url, stream=True)
            if response.status_code == 200:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                save_dir = os.path.join(script_dir, '__pycache__')
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)
                file_name = song_name + song_arname +get_file_extension(song_url)
                valid_chars = "/\\*?:\"\'|<>"
                file_name = ''.join((c if c not in valid_chars else "_") for c in file_name)
                file_path = os.path.join(save_dir, file_name)
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                # download_link = f'<a href="{song_url}" download="{file_name}">Click here to download {file_name}</a>'
            else:
                return "下载失败！", None
    else:
        return "信息获取不完整！", None

    return file_path,{
            "status": 200,
            "name": song_name,
            "pic": song_picUrl,
            "ar_name": song_arname,
            "al_name": song_alname,
            "level":music_level1(jseg['data'][0]['level']),
            "size": size(jseg['data'][0]['size']),
            "url": song_url,
            "lyric": lyricjse['lrc']['lyric'],
            "tlyric": lyricjse['tlyric']['lyric']
        }

#defalt 97.65MB
def test():
    url = "https://music.163.com/#/song?id=1306371615"
    level = "高清环绕声"
    _,data = process_song_v1(url, level)
    if data["size"] == "97.65MB":
        return True
    else:
        print(data["size"])
        return False

import re

def lyrics_to_srt(lyrics):
    lines = lyrics.strip().split('\n')
    srt_lines = []
    subtitle_number = 1
    
    for i in range(len(lines) - 1):
        current_line = lines[i]
        next_line = lines[i + 1]
        
        # Extract the time and text using regex
        match_current = re.match(r'\[(\d{2}):(\d{2}).(\d{2})\] (.+)', current_line)
        match_next = re.match(r'\[(\d{2}):(\d{2}).(\d{2})\] (.+)', next_line)
        
        if match_current and match_next:
            minutes_current, seconds_current, milliseconds_current, text_current = match_current.groups()
            minutes_next, seconds_next, milliseconds_next, _ = match_next.groups()
            
            start_time = f"{minutes_current}:{seconds_current},{milliseconds_current}0"
            end_time = f"{minutes_next}:{seconds_next},{milliseconds_next}0"
            
            # Add subtitle to SRT list
            srt_lines.append(f"{subtitle_number}")
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.append(text_current)
            srt_lines.append("")  # Empty line for SRT separation
            
            subtitle_number += 1
    
    # Handle the last line
    last_line = lines[-1]
    match_last = re.match(r'\[(\d{2}):(\d{2}).(\d{2})\] (.+)', last_line)
    
    if match_last:
        minutes_last, seconds_last, milliseconds_last, text_last = match_last.groups()
        start_time_last = f"{minutes_last}:{seconds_last},{milliseconds_last}0"
        
        # Assume the last subtitle lasts 3 seconds for example purposes
        end_time_last = f"{minutes_last}:{int(seconds_last)+3},{milliseconds_last}0"
        
        srt_lines.append(f"{subtitle_number}")
        srt_lines.append(f"{start_time_last} --> {end_time_last}")
        srt_lines.append(text_last)
    
    return "\n".join(srt_lines)

def lyrics_to_lrc(lyrics):
    lines = lyrics.strip().split("\n")
    lrc_lines = []

    for line in lines:
        if line.strip():
            lrc_lines.append(line)

    return "\n".join(lrc_lines)

def generate_files(data):
    if data.get('lyric'):
        lyrics = data['lyric']
    else:
        return None, None
    srt_content = lyrics_to_srt(lyrics)
    lrc_content = lyrics_to_lrc(lyrics)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    save_dir = os.path.join(script_dir, '__pycache__')
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    srt_path = os.path.join(script_dir, '__pycache__', f'{data["name"]}.srt')
    lrc_path = os.path.join(script_dir, '__pycache__',f'{data["name"]}.lrc')

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    with open(lrc_path, "w", encoding="utf-8") as f:
        f.write(lrc_content)

    return srt_path, lrc_path

def delete_cache():
    folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '__pycache__')
    try:
        # 确保路径存在并且是一个文件夹
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            return f"Successfully deleted the folder: {folder_path}"
        else:
            return f"Folder does not exist: {folder_path}"
    except Exception as e:
        return f"An error occurred: {str(e)}"

global cookie_flag
cookie_flag = False

def main(url, vip, level):
    global cookie_flag
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cookie_file = os.path.join(script_dir, 'cookie.txt')
    with open(cookie_file, 'a'):
        pass
    cm = CookieManager(file_path=cookie_file)
    if vip in ["VIP", "SVIP"] and not cookie_flag:
        if not test():
            print("cookie无效，请重新登录")
            cm.login_and_save_cookies()
        else:
            print("cookie有效")
            cookie_flag = True

    
    # 获取文件名和数据
    download_link, data = process_song_v1(url, level)
    
    # 如果成功获取了数据
    if download_link and data:
        # 返回文件下载链接和显示的信息
        display_text = (
            f"🎵 歌曲名: {data['name']}\n"
            f"🎤 歌手: {data['ar_name']}\n"
            f"💿 专辑: {data['al_name']}\n"
            f"🎧 音质: {data['level']}\n"
            f"📏 文件大小: {data['size']}\n"
            f"🌐 下载链接: {data['url']}\n"
        )
        if data['pic']:
            display_text += f"🖼 专辑封面: ![album cover]({data['pic']})\n"
        
        # 处理歌词信息
        if data.get('lyric'):
            # display_text += f"\n🎶 歌词:\n{data['lyric']}\n"
            srt_path, lrc_path = generate_files(data)

        return download_link, lrc_path,display_text
    else:
        return None, "无法获取歌曲信息，请检查URL或音质设置。"



# 音质等级选项，根据VIP状态定义
quality_options = {
    "普通用户": ["标准音质", "极高音质"],
    "VIP": ["标准音质", "极高音质", "无损音质", "Hires音质", "高清环绕声"],
    "SVIP": ["标准音质", "极高音质", "无损音质", "Hires音质", "沉浸环绕声", "高清环绕声", "超清母带"]
}

def update_quality_options(vip_status):
    # 根据VIP状态返回更新后的音质等级选项
    return quality_options.get(vip_status, [])

def on_vip_status_change(vip_status):
    # 获取根据VIP状态更新的音质等级选项
    new_options = update_quality_options(vip_status)
    # 返回更新后的选项以及第一个选项作为默认值
    return gr.update(choices=new_options, value=new_options[0] if new_options else None)

def delete_directory(req: gr.Request):
    if not req.username:
        return
    current_dir = Path(__file__).parent
    user_dir: Path = current_dir / req.username
    shutil.rmtree(str(user_dir))

header = """
# 网易云音乐无损解析GUI界面🌈🎵

⚠️此项目完全开源免费 （[项目地址](https://github.com/IggyMeraki/Netease_url_gui)），切勿进行盈利，所造成的后果与本人无关。
"""

short_js = """
<script src="https://cdn.staticfile.org/jquery/1.10.2/jquery.min.js" rel="external nofollow"></script>
<script src="https://static.geetest.com/static/js/gt.0.4.9.js"></script>
"""

custom_css = """
.pay_qrcode img {
  width: 300px !important;
  height: 300px !important;
  margin-top: 20px; /* 避免二维码头部的说明文字挡住二维码 */
}
"""

# Gradio界面设计
if __name__ == "__main__":
    with gr.Blocks(head=short_js, css=custom_css,delete_cache=(86400,86400)) as interface:

        gr.Markdown(header)
        with gr.Row():
            url_input = gr.Textbox(label="URL", placeholder="请输入歌曲URL,如https://music.163.com/#/song?id=1306371615")
            vip_status_dropdown = gr.Dropdown(
                label="账号VIP状态", 
                choices=["普通用户", "VIP", "SVIP"], 
                value="普通用户"
            )
            quality_dropdown = gr.Dropdown(
                label="音质等级",
                choices=quality_options["普通用户"],  # 初始选项
                value="标准音质"
            )

        vip_status_dropdown.change(on_vip_status_change, inputs=vip_status_dropdown, outputs=quality_dropdown)
        
        submit_btn = gr.Button("提交")
        download = gr.File(label="下载音乐")
        # srt_download = gr.File(label="下载歌词(SRT)")
        lrc_download = gr.File(label="下载歌词(LRC)")
        output_text = gr.Textbox(label="歌曲信息")
        delete_button = gr.Button("清除缓存")
        delete_button.click(delete_cache,outputs=[output_text])

        submit_btn.click(main, inputs=[url_input, vip_status_dropdown, quality_dropdown], outputs=[download, lrc_download, output_text])

        # interface.unload(delete_directory)

    interface.launch(inbrowser=True)
