import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class FileSnapshot:
    path: Path
    content: Optional[str]  # 原内容，None 表示修改前文件并不存在
    existed: bool
    size: int = 0
    modified_time: float = 0.0


@dataclass
class Checkpoint:
    id: str
    timestamp: float
    description: str
    files: Dict[Path, FileSnapshot] = field(default_factory=dict)

    def summary(self) -> str:
        file_names = ", ".join([p.name for p in self.files.keys()])
        time_str = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        return f"[{time_str}] {self.description} ({len(self.files)} 个文件: {file_names})"


class SnapshotManager:
    """
    原子版本安全网引擎 (Atomic Safety Net & Shadow Snapshot Engine)
    在 Agent 修改任何文件前记录原始副本，支持秒级 /undo 原子回滚。
    """
    def __init__(self, max_stack_size: int = 30):
        self.max_stack_size = max_stack_size
        self._undo_stack: List[Checkpoint] = []
        self._pending_files: Dict[Path, FileSnapshot] = {}
        self._pending_desc: str = ""

    def record_before_change(self, file_path: str | Path, desc: str = ""):
        """
        在文件被物理写入前记录快照。
        若当前事务/步骤内已记录过该文件，则严格保留最开始的原始状态。
        """
        p = Path(file_path).resolve()
        if p in self._pending_files:
            return  # 保持当前事务最开头的原始状态

        if p.exists() and p.is_file():
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                self._pending_files[p] = FileSnapshot(
                    path=p,
                    content=content,
                    existed=True,
                    size=len(content),
                    modified_time=p.stat().st_mtime
                )
            except Exception:
                try:
                    with open(p, "rb") as f:
                        b_content = f.read()
                    self._pending_files[p] = FileSnapshot(
                        path=p,
                        content=b_content.decode("utf-8", errors="replace"),
                        existed=True,
                        size=len(b_content),
                        modified_time=p.stat().st_mtime
                    )
                except Exception:
                    pass
        else:
            # 文件修改前尚不存在（如即将 write_file 创建新文件）
            self._pending_files[p] = FileSnapshot(
                path=p,
                content=None,
                existed=False,
                size=0,
                modified_time=0.0
            )

        if not self._pending_desc:
            self._pending_desc = desc or f"修改 {p.name}"

    def has_pending(self) -> bool:
        """检查是否有已发生但未打包成 Checkpoint 的文件修改"""
        return bool(self._pending_files)

    def commit_checkpoint(self, description: str = "") -> Optional[Checkpoint]:
        """
        将当前暂存的所有文件修改打包提交为一个原子 Checkpoint 压入 Undo 栈
        """
        if not self._pending_files:
            return None

        desc = description or self._pending_desc or "文件代码修改"
        ckpt_id = f"ckpt_{int(time.time() * 1000)}"
        checkpoint = Checkpoint(
            id=ckpt_id,
            timestamp=time.time(),
            description=desc,
            files=dict(self._pending_files)
        )
        self._undo_stack.append(checkpoint)

        # 保持栈容量合理
        if len(self._undo_stack) > self.max_stack_size:
            self._undo_stack.pop(0)

        # 清空当前暂存
        self._pending_files = {}
        self._pending_desc = ""
        return checkpoint

    def rollback_latest(self) -> Tuple[bool, str, List[Path]]:
        """
        执行秒级原子回退：弹出最近一次 Checkpoint 并精准恢复文件系统状态
        返回: (成功: bool, 状态描述: str, 被还原的文件列表: List[Path])
        """
        # 如果当前有未 commit 的变更且栈为空，先自动打包
        if not self._undo_stack and self._pending_files:
            self.commit_checkpoint("最近未提交修改")

        if not self._undo_stack:
            return False, "当前没有可回滚的历史记录（Undo 栈为空）。", []

        checkpoint = self._undo_stack.pop()
        reverted_files: List[Path] = []
        errors: List[str] = []

        for path, snap in checkpoint.files.items():
            try:
                if snap.existed:
                    # 恢复原文件内容
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(snap.content or "")
                    reverted_files.append(path)
                else:
                    # 新增的文件：回滚即从磁盘彻底删除
                    if path.exists() and path.is_file():
                        path.unlink()
                    reverted_files.append(path)
            except Exception as e:
                errors.append(f"还原 {path.name} 失败: {str(e)}")

        msg_parts = [f"✅ 已成功原子回退检查点: {checkpoint.description}"]
        if reverted_files:
            msg_parts.append(f"共恢复/删除 {len(reverted_files)} 个文件: " + ", ".join([p.name for p in reverted_files]))
        if errors:
            msg_parts.append("⚠️ 部分异常: " + "; ".join(errors))

        return True, "\n".join(msg_parts), reverted_files

    def get_stack_summary(self) -> List[Dict[str, Any]]:
        """获取当前 Undo 栈内所有可回滚检查点的清单"""
        result = []
        for idx, ckpt in enumerate(reversed(self._undo_stack)):
            result.append({
                "step": idx + 1,
                "id": ckpt.id,
                "description": ckpt.description,
                "time": time.strftime("%H:%M:%S", time.localtime(ckpt.timestamp)),
                "files": [p.name for p in ckpt.files.keys()]
            })
        return result

    def clear(self):
        """清空回滚栈"""
        self._undo_stack.clear()
        self._pending_files.clear()
        self._pending_desc = ""


default_snapshot_manager = SnapshotManager()
