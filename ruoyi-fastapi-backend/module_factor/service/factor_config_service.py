"""
因子配置文件服务：基于项目目录下的配置文件，提供列表与内容读取。
配置目录约定：项目根下 config/train，仅扫描 .txt 文件。
"""

import os
from pathlib import Path
from typing import List

from utils.log_util import logger

# 项目根目录（backend 的上级的上级：ruoyi-fastapi-backend -> 项目根）
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
DEFAULT_CONFIG_DIR = _PROJECT_ROOT / 'config' / 'train'


def _parse_factor_codes_from_lines(lines: List[str]) -> List[str]:
    """
    解析行列表为因子代码列表。
    支持：每行 category__feature_name 或 category,feature_name；或每行一个因子代码。
    空行与 # 开头的行忽略。
    """
    codes: List[str] = []
    for line in lines:
        raw = line.strip()
        if not raw or raw.startswith('#'):
            continue
        if '__' in raw:
            parts = raw.split('__', 1)
            if len(parts) == 2 and all(p.strip() for p in parts):
                codes.append(f"{parts[0].strip()}__{parts[1].strip()}")
        elif ',' in raw:
            parts = raw.split(',', 1)
            if len(parts) == 2 and all(p.strip() for p in parts):
                codes.append(f"{parts[0].strip()}__{parts[1].strip()}")
        else:
            codes.append(raw)
    return codes


def _read_and_parse_factor_codes(file_path: Path) -> List[str]:
    """读取文件并解析为因子代码列表。"""
    if not file_path.exists():
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return _parse_factor_codes_from_lines(lines)
    except Exception as e:
        logger.warning('读取因子配置文件失败: %s, path=%s', e, file_path)
        return []


def get_config_dir() -> Path:
    """返回因子配置目录（绝对路径）。若不存在则返回默认路径，调用方可再判断 exists。"""
    return DEFAULT_CONFIG_DIR


def list_configs() -> List[dict]:
    """
    扫描 config/train 下所有 .txt 文件，返回列表。
    返回项: { "name": 文件名, "path": 用于 content 接口的 path（当前为文件名）, "factorCount": 因子数量 }
    """
    config_dir = get_config_dir()
    result: List[dict] = []
    if not config_dir.exists():
        logger.info('因子配置目录不存在: %s', config_dir)
        return result
    try:
        for p in sorted(config_dir.iterdir()):
            if p.is_file() and p.suffix.lower() == '.txt':
                codes = _read_and_parse_factor_codes(p)
                result.append({
                    'name': p.name,
                    'path': p.name,
                    'factorCount': len(codes),
                })
    except Exception as e:
        logger.error('扫描因子配置目录失败: %s', e)
    return result


def get_content(path_param: str) -> tuple[str | None, str | None]:
    """
    根据 path 读取配置文件内容，解析为换行分隔的 factorCodes（与配置文件格式一致）。
    path 仅允许文件名或相对 config/train 的子路径，禁止 .. 越界。
    返回 (factor_codes_string, error_message)。成功时 error_message 为 None。
    """
    config_dir = get_config_dir().resolve()
    # 禁止 .. 和绝对路径
    if '..' in path_param or path_param.startswith('/') or (len(path_param) > 1 and path_param[1] == ':'):
        return None, '路径不允许越界或使用绝对路径'
    path_param = path_param.strip()
    if not path_param:
        return None, '路径不能为空'
    target = (config_dir / path_param).resolve()
    if not target.is_file():
        return None, '文件不存在或不是文件'
    try:
        target.relative_to(config_dir)
    except ValueError:
        return None, '路径必须在配置目录内'
    codes = _read_and_parse_factor_codes(target)
    # 因子之间用换行分隔，与配置文件格式一致
    return '\n'.join(codes), None
