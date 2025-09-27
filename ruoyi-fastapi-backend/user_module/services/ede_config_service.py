# -- coding: utf-8 --
import json
import os
from typing import Dict, Any
from pathlib import Path


class EDEConfigService:
    """EDE配置服务，负责从配置文件加载指标配置"""
    
    _config_cache: Dict[str, Any] = {}
    _config_loaded = False
    
    @classmethod
    def load_config_from_file(cls, config_file_path: str = None) -> Dict[str, Any]:
        """
        从配置文件加载EDE配置
        
        Args:
            config_file_path: 配置文件路径，如果为None则使用默认路径
            
        Returns:
            Dict: 配置字典
        """
        print('-----------------------------')
        if cls._config_loaded and cls._config_cache:
            return cls._config_cache
        
        if config_file_path is None:
            # 默认配置文件路径（相对于项目根目录的共享配置）
            current_dir = Path(__file__).parent.parent.parent.parent
            config_file_path = current_dir / "shared-config" / "ede_config.json"
        
        try:
            # 检查文件是否存在
            if not os.path.exists(config_file_path):
                print(f"配置文件不存在: {config_file_path}")
            
            # 读取JSON配置文件
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            cls._config_cache = config
            cls._config_loaded = True
            print('-----------------------------',config)
            print(f"成功加载EDE配置，共{len(config)}个指标配置")
            return config

        except Exception as e:
            print(f"加载配置文件失败: {e}")

    
    @classmethod
    def get_config(cls, config_key: str = None) -> Any:
        """
        获取配置
        
        Args:
            config_key: 配置键，如果为None则返回所有配置
            
        Returns:
            配置数据
        """
        if not cls._config_loaded:
            cls.load_config_from_file()
        
        if config_key is None:
            return cls._config_cache
        
        return cls._config_cache.get(config_key)
    
    @classmethod
    def reload_config(cls) -> Dict[str, Any]:
        """重新加载配置"""
        cls._config_loaded = False
        cls._config_cache = {}
        return cls.load_config_from_file()
