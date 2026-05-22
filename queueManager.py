from collections import deque
import threading
import time
import uuid

from getGlobalLogger import logger
from loadSettings import loadSettings

# 简单的任务超时设置 (秒)
TASK_QUEUE_TIMEOUT_SECONDS = loadSettings("TASK_QUEUE_TIMEOUT_SECONDS")

class TaskQueueManager:
    def __init__(self):
        self.task_queue = deque()  # 存储 {'id': task_id, 'name': task_name, 'added_at': timestamp}
        self.currently_processing_task_id = None
        self.lock = threading.Lock()

    def _cleanup_timed_out_tasks(self):
        """内部方法：清理队列中超时的任务，不应直接从外部调用，除非持有锁"""
        now = time.time()
        removed_count = 0
        # 创建一个列表来存储要保留的任务，以避免在迭代时修改 deque
        kept_tasks = deque()
        
        # 先把正在处理的任务（如果有）放到保留队列
        processing_task_details = None
        if self.currently_processing_task_id:
            # 通常正在处理的任务不应该在等待队列中，但以防万一
            for task in self.task_queue:
                if task['id'] == self.currently_processing_task_id:
                    processing_task_details = task
                    break
            if processing_task_details:
                kept_tasks.append(processing_task_details)

        for task in self.task_queue:
            if task['id'] == self.currently_processing_task_id: # 如果它仍在队列中且是当前处理的，保留它
                if task not in kept_tasks: kept_tasks.append(task) # 确保不重复添加
                continue

            if (now - task['added_at']) > TASK_QUEUE_TIMEOUT_SECONDS:
                logger.info(f"任务超时被移除: {task['id']}, 名称: {task['name']}")
                removed_count += 1
            else:
                # 如果任务未超时，并且不是当前正在处理的任务，则保留
                # (当前处理的任务已在上面单独处理过)
                if task not in kept_tasks: kept_tasks.append(task)
        
        if removed_count > 0 or len(kept_tasks) != len(self.task_queue) :
            self.task_queue = kept_tasks
        return removed_count

    def add_task(self, task_name="未命名任务"):
        with self.lock:
            self._cleanup_timed_out_tasks() 
            task_id = str(uuid.uuid4())
            timestamp = time.time()
            self.task_queue.append({'id': task_id, 'name': task_name, 'added_at': timestamp})
            logger.info(f"任务已添加: {task_id}, 名称: {task_name}, 队列长度: {len(self.task_queue)}")
            return task_id

    def get_task_position_and_is_processing_another(self, task_id):
        with self.lock:
            self._cleanup_timed_out_tasks()
            if self.currently_processing_task_id == task_id:
                return -1, False 

            is_another_processing = self.currently_processing_task_id is not None

            # 转换为列表以安全迭代
            current_queue_snapshot = list(self.task_queue)
            for i, task_details in enumerate(current_queue_snapshot):
                if task_details['id'] == task_id:
                    return i, is_another_processing
            
            return -2, is_another_processing

    def attempt_to_start_processing(self, task_id):
        with self.lock:
            self._cleanup_timed_out_tasks()

            if self.currently_processing_task_id is not None:
                logger.debug(f"尝试开始 {task_id} 失败: 另一个任务 {self.currently_processing_task_id} 正在处理中。")
                return False 

            if not self.task_queue:
                logger.debug(f"尝试开始 {task_id} 失败: 队列为空。")
                return False
            
            # 再次检查任务是否还在队列中
            if not any(t['id'] == task_id for t in self.task_queue):
                logger.info(f"尝试开始任务 {task_id} 失败：任务已不在队列中（可能已超时或被移除）。")
                return False

            if self.task_queue[0]['id'] == task_id:
                self.currently_processing_task_id = task_id
                logger.info(f"任务 {task_id} ({self.task_queue[0]['name']}) 开始处理。")
                return True
            else:
                logger.debug(f"尝试开始 {task_id} 失败: 它不在队首。队首是 {self.task_queue[0]['id'] if self.task_queue else 'N/A'}")
                return False

    def finish_processing(self, task_id):
        with self.lock:
            if self.currently_processing_task_id == task_id:
                task_name_finished = "未知任务"
                # 从队列中移除已完成的任务
                if self.task_queue and self.task_queue[0]['id'] == task_id:
                    task_name_finished = self.task_queue[0]['name']
                    self.task_queue.popleft()
                
                self.currently_processing_task_id = None
                logger.info(f"任务 {task_id} ({task_name_finished}) 处理完成。新队列长度: {len(self.task_queue)}")
                return True
            logger.warning(f"尝试完成一个不匹配或未开始的任务: 当前处理 {self.currently_processing_task_id}, 尝试完成 {task_id}")
            return False

    def remove_task_if_exists_and_not_processing(self, task_id):
        with self.lock:
            if self.currently_processing_task_id == task_id:
                logger.debug(f"任务 {task_id} 正在被处理，不应由 remove_task_if_exists_and_not_processing 移除。")
                return False

            initial_len = len(self.task_queue)
            task_name_removed = "未知任务"
            
            # 查找任务以获取名称
            task_to_remove_details = next((task for task in self.task_queue if task['id'] == task_id), None)
            if task_to_remove_details:
                task_name_removed = task_to_remove_details['name']

            new_queue = deque(task for task in self.task_queue if task['id'] != task_id)
            if len(new_queue) < initial_len:
                self.task_queue = new_queue
                logger.info(f"任务 {task_id} ({task_name_removed}) 已从等待队列中移除。新队列长度: {len(self.task_queue)}")
                return True
            logger.debug(f"尝试移除任务 {task_id} ({task_name_removed}) 失败，任务未在等待队列中找到。")
            return False

# 全局单例
QUEUE_MANAGER = TaskQueueManager()