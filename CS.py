import psutil
import time
from pypresence import Presence
import threading
import os
import sys
import logging
from datetime import datetime
import platform

# 配置日志记录（确保路径正确）
log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'douyin_tray.log')
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 你的Discord应用Client ID
client_id = "1392452318464573582"
RPC = None
running_event = threading.Event()

# 抖音状态更新函数（简化版，仅检测进程）
def update_douyin_status():
    logging.info("状态更新线程已启动")
    last_status = False
    
    while running_event.is_set():
        try:
            # 检测抖音进程
            is_douyin_running = any(
                "douyin.exe" in p.name().lower() or
                "douyin" in p.name().lower()
                for p in psutil.process_iter()
            )
            
            if is_douyin_running:
                if not last_status:  # 状态变化时才更新
                    logging.info("检测到抖音运行，更新Discord状态")
                    RPC.update(
                        details="Using Douyin",
                        state="Browsing videos",
                        large_image="douyin",
                        large_text="Douyin Desktop",
                        instance=False
                    )
                last_status = True
            else:
                if last_status or RPC:  # 状态变化或RPC已初始化时清除
                    logging.info("未检测到抖音运行，清除Discord状态")
                    RPC.clear_activity()
                    last_status = False
                    
        except Exception as e:
            logging.error(f"状态更新错误: {str(e)}")
        
        time.sleep(5)  # 每5秒检测一次

# 创建系统托盘图标（使用pystray）
def create_system_tray():
    try:
        import pystray
        from PIL import Image, ImageDraw
        
        # 创建简单的图标
        def create_image(width, height):
            image = Image.new('RGBA', (width, height), (255, 0, 0, 255))  # 红色图标
            draw = ImageDraw.Draw(image)
            draw.rectangle((10, 10, width-10, height-10), fill=(255, 255, 255, 255))
            return image
        
        # 托盘菜单项
        def on_quit(icon, item):
            logging.info("用户选择退出")
            running_event.clear()
            time.sleep(1)  # 等待线程结束
            if RPC:
                RPC.clear_activity()
                RPC.close()
            icon.stop()
            sys.exit()
        
        menu = (
            pystray.MenuItem('退出', on_quit),
        )
        
        # 创建托盘图标
        icon = pystray.Icon(
            "douyin-tray",
            create_image(64, 64),
            "抖音状态同步",
            menu
        )
        
        # 启动状态更新线程
        status_thread = threading.Thread(target=update_douyin_status)
        status_thread.daemon = True
        status_thread.start()
        
        # 运行托盘应用
        logging.info("系统托盘已启动")
        icon.run()
        
    except Exception as e:
        logging.critical(f"创建系统托盘失败: {str(e)}")
        # 回退到无托盘模式
        fallback_mode()

# 无托盘模式（后台静默运行）
def fallback_mode():
    logging.info("进入无托盘模式")
    
    # 启动状态更新线程
    status_thread = threading.Thread(target=update_douyin_status)
    status_thread.daemon = True
    status_thread.start()
    
    # 保持主线程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        running_event.clear()
        time.sleep(1)
        if RPC:
            RPC.clear_activity()
            RPC.close()
        sys.exit()

# 主函数
def main():
    logging.info("程序启动")
    
    try:
        # 初始化Discord RPC
        global RPC
        RPC = Presence(client_id)
        RPC.connect()
        logging.info(f"Discord RPC连接成功 (Client ID: {client_id})")
        
        # 设置运行标志
        running_event.set()
        
        # 尝试创建系统托盘
        try:
            import pystray
            logging.info("使用pystray创建系统托盘")
            create_system_tray()
        except ImportError:
            logging.warning("缺少pystray库，使用无托盘模式")
            fallback_mode()
            
    except Exception as e:
        logging.critical(f"程序初始化失败: {str(e)}")
        if RPC:
            RPC.clear_activity()
            RPC.close()
        sys.exit(1)

if __name__ == "__main__":
    main()
