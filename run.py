import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from main import main
    if __name__ == "__main__":
        main()
except Exception as e:
    print(f"启动错误: {e}")
    input("按回车退出...")