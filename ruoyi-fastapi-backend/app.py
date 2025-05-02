import uvicorn
from server import app, AppConfig  # noqa: F401


if __name__ == '__main__':
    uvicorn.run(
        app='app:app',
        host=AppConfig.app_host,
        port=AppConfig.app_port,
        root_path=AppConfig.app_root_path,
        reload=AppConfig.app_reload,
        timeout_keep_alive=60,          # 空闲连接保持时间
        timeout_graceful_shutdown=60    # 关闭时等待请求完成的时间

    )
