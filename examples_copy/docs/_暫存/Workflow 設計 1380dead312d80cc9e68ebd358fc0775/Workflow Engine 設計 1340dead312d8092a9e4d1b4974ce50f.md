# Workflow Engine 設計

思考

- workflow runner 是在前端還是後端？
    - 若是在前端，簡單來講就是照著 workflow json 的步驟來逐一執行
        - 但遇到像是要連接資料庫、secret等等，要怎樣處理？ → 好像只能在後端（？）
    - 若是在後端
        - 要怎樣叫前端給予適當的介面？應該說，前端要如何設計？
    - ⇒
        - 前後端都要有 workflow json，前端用於顯示，例如當前的node需要user action，後端用於執行workflow runner
        - 兩者用 websocket 連接，當遇到需要等待的情況（user action、其他…），runner 會等待一定時間，若超時斷開ws、暫停當前 workflow、釋放資源
            - 前端當 call ws 沒有回應，就知道這個 flow 已經被暫停了
        - 前端要如何恢復 workflow？
            - 假設是等待 user action 的情況，UI 應該是會顯示當前進度是卡在 user action ＆ 提供 user 輸入介面，一旦 user 做了 action，前端 call api 叫後端恢復，建立新的 websocket

```markdown

1. 工作流遇到需要用戶操作的節點
   ↓
2. 創建任務記錄並暫停工作流
   ↓
3. 通過多個渠道通知相關用戶
   ↓
4. 用戶收到通知並查看任務
   ↓
5. [等待期間]
   - 定期發送提醒
   - 支持通過多個入口完成任務
   - 保持任務狀態可查詢
   ↓
6. 用戶完成任務
   ↓
7. 更新任務狀態並恢復工作流

---

1. 工作流初始化
   ├─ 載入工作流定義
   ├─ 建立 WebSocket 連接
   ├─ 同步初始狀態
   └─ 開始執行

2. 節點執行
   ├─ 同步節點
   │  ├─ 直接執行業務邏輯
   │  ├─ 通過 WS 更新狀態
   │  └─ 繼續下一節點
   │
   └─ 異步節點
      ├─ 用戶輸入類
      │  ├─ 準備 UI 資源
      │  ├─ 通過 WS 請求用戶輸入
      │  ├─ 設置等待超時
      │  └─ 等待響應
      │     ├─ 及時響應 → 繼續執行
      │     └─ 超時等待 → 進入休眠
      │
      ├─ 系統等待類
      │  ├─ 註冊觸發條件
      │  ├─ 設置回調機制
      │  └─ 進入休眠
      │
      └─ 人工任務類
         ├─ 創建任務記錄
         ├─ 分配執行人
         ├─ 發送通知
         └─ 進入休眠

3. 休眠處理
   ├─ 保存完整執行狀態
   ├─ 設置喚醒觸發器
   ├─ 關閉 WebSocket 連接
   └─ 釋放執行資源

4. 喚醒與恢復
   ├─ 收到恢復信號（API調用）
   ├─ 重建執行環境
   ├─ 建立新的 WS 連接
   ├─ 載入執行狀態
   ├─ 驗證恢復條件
   └─ 繼續執行下一節點
```

---

## 1. **核心组件**

```
WorkflowEngine（主要入口）
├── WorkflowRunner（执行引擎）
├── WorkflowStorage（存储引擎）
└── TriggerManager（触发器管理器）

```

## 2. **数据结构**

### 2.1 节点（Nodes）和边（Edges）

采用图结构表示工作流，其中：

- *节点（nodes）：**表示工作流中的各个操作单元，如触发器、条件判断、HTTP请求等。
- *边（edges）：**表示节点之间的连接关系和执行顺序，包括条件分支等信息。

### 2.2 工作流定义示例

```json
{
    "id": "workflow_1",
    "name": "示例工作流",
    "nodes": [
        {
            "id": "node_1",
            "type": "webhook",  // 触发器节点
            "config": {
                "path": "/webhook/123",
                "method": "POST"
            }
        },
        {
            "id": "node_2",
            "type": "if",
            "config": {
                "condition": "data.amount > 1000"
            }
        },
        {
            "id": "node_3",
            "type": "action",
            "config": {
                "action_name": "approve"
            }
        },
        {
            "id": "node_4",
            "type": "action",
            "config": {
                "action_name": "reject"
            }
        }
    ],
    "edges": [
        {
            "from": "node_1",
            "to": "node_2"
        },
        {
            "from": "node_2",
            "to": "node_3",
            "condition": "true"
        },
        {
            "from": "node_2",
            "to": "node_4",
            "condition": "false"
        }
    ]
}

```

## 3. **核心类**

### 3.1 节点注册表

```python
class NodeRegistry:
    _registry = {}

    @classmethod
    def register(cls, node_type):
        def wrapper(node_class):
            cls._registry[node_type] = node_class
            return node_class
        return wrapper

    @classmethod
    def get_node_class(cls, node_type):
        return cls._registry.get(node_type)

```

### 3.2 节点配置验证

使用 `pydantic` 库进行配置验证。

```python
from pydantic import BaseModel, ValidationError

# 基础节点配置模型
class BaseNodeConfig(BaseModel):
    pass

# 基础节点类
class BaseNode:
    config_schema = BaseNodeConfig

    def __init__(self, config: dict):
        try:
            self.config = self.config_schema(**config)
        except ValidationError as e:
            errors = e.errors()
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in errors]
            error_str = "; ".join(error_messages)
            raise ValueError(f"配置验证失败：{error_str}")

    async def execute(self, input_data: dict) -> dict:
        raise NotImplementedError()

```

### 3.3 节点类型定义

### 3.3.1 IfNode（条件判断节点）

```python
@NodeRegistry.register("if")
class IfNode(BaseNode):
    class ConfigSchema(BaseNodeConfig):
        condition: str

    config_schema = ConfigSchema

    async def execute(self, input_data: dict) -> dict:
        condition = self.config.condition
        result = eval(condition, {}, input_data)
        output_key = "true" if result else "false"
        return {"__output__": output_key}

```

### 3.3.2 SwitchNode（多路分支节点）

```python
@NodeRegistry.register("switch")
class SwitchNode(BaseNode):
    class ConfigSchema(BaseNodeConfig):
        variable: str
        cases: list

    config_schema = ConfigSchema

    async def execute(self, input_data: dict) -> dict:
        variable_name = self.config.variable
        cases = self.config.cases
        value = eval(variable_name, {}, input_data)
        output_key = str(value) if value in cases else "default"
        return {"__output__": output_key}

```

### 3.3.3 其他节点

其他节点按照相同的模式定义，并在 `NodeRegistry` 中注册。

### 3.4 工作流存储（WorkflowStorage）

```python
class WorkflowStorage:
    def save_workflow(self, workflow_def: dict):
        """保存工作流定义到数据库或文件系统"""
        pass

    def load_workflow(self, workflow_id: str) -> dict:
        """从数据库或文件系统加载工作流定义"""
        pass

    def list_workflows(self) -> list:
        """列出所有已保存的工作流"""
        pass

```

### 3.5 触发器管理器（TriggerManager）

```python
class TriggerManager:
    def __init__(self):
        self.triggers = {}  # workflow_id -> trigger_node
        self.workflow_runner = None

    def set_workflow_runner(self, runner):
        self.workflow_runner = runner

    async def add_trigger(self, workflow_id: str, trigger_node: BaseNode):
        """注册触发器"""
        self.triggers[workflow_id] = trigger_node
        await trigger_node.activate()

    async def remove_trigger(self, workflow_id: str):
        """移除触发器"""
        if workflow_id in self.triggers:
            await self.triggers[workflow_id].deactivate()
            del self.triggers[workflow_id]

    async def on_trigger(self, workflow_id: str, trigger_data: dict):
        """当触发器被触发时调用"""
        if self.workflow_runner:
            await self.workflow_runner.execute_workflow(workflow_id, trigger_data)

```

### 3.6 工作流执行引擎（WorkflowRunner）

```python
class WorkflowRunner:
    def __init__(self):
        self.storage = WorkflowStorage()

    async def _create_node(self, node_def: dict) -> BaseNode:
        node_type = node_def["type"]
        node_class = NodeRegistry.get_node_class(node_type)
        if not node_class:
            raise ValueError(f"未知的节点类型：{node_type}")

        try:
            node_instance = node_class(config=node_def.get("config", {}))
            return node_instance
        except ValueError as e:
            raise ValueError(f"节点 '{node_def['id']}' 的配置无效：{e}")

    async def execute_workflow(self, workflow_id: str, trigger_data: dict = None):
        try:
            workflow_def = self.storage.load_workflow(workflow_id)
            nodes = {}
            for node_def in workflow_def["nodes"]:
                nodes[node_def["id"]] = await self._create_node(node_def)

            edges = workflow_def["edges"]
            node_results = {}
            # 初始化当前节点
            if trigger_data:
                current_node_id = workflow_def["nodes"][0]["id"]
                node_results[current_node_id] = trigger_data
            else:
                current_node_id = workflow_def["nodes"][0]["id"]

            # 动态执行节点
            while current_node_id:
                current_node = nodes[current_node_id]
                input_data = self._get_node_input(current_node_id, edges, node_results)
                result = await current_node.execute(input_data)
                node_results[current_node_id] = result
                # 根据执行结果选择下一个节点
                current_node_id = self._get_next_node_id(current_node_id, result, edges)

            return node_results
        except Exception as e:
            print(f"执行工作流时发生错误：{e}")

    def _get_node_input(self, node_id, edges, node_results):
        # 获取节点的输入数据
        # 实现略，需根据实际需求编写
        pass

    def _get_next_node_id(self, current_node_id, result, edges):
        outputs = result.get("__output__")
        for edge in edges:
            if edge["from"] == current_node_id:
                condition = edge.get("condition")
                if condition:
                    if condition == outputs:
                        return edge["to"]
                else:
                    # 默认连接
                    return edge["to"]
        return None  # 无后续节点，结束

```

### 3.7 工作流引擎（WorkflowEngine）

```python
class WorkflowEngine:
    def __init__(self):
        self.storage = WorkflowStorage()
        self.trigger_manager = TriggerManager()
        self.workflow_runner = WorkflowRunner()

        # 设置相互引用
        self.trigger_manager.set_workflow_runner(self.workflow_runner)

    async def start(self):
        """启动引擎"""
        # 加载所有工作流
        workflows = self.storage.list_workflows()

        # 注册触发器
        for workflow_def in workflows:
            if self._is_triggered_workflow(workflow_def):
                trigger_node = await self.workflow_runner._create_node(workflow_def["nodes"][0])
                await self.trigger_manager.add_trigger(workflow_def["id"], trigger_node)

    async def stop(self):
        """停止引擎"""
        # 停止所有触发器
        for workflow_id in list(self.trigger_manager.triggers.keys()):
            await self.trigger_manager.remove_trigger(workflow_id)

    def _is_triggered_workflow(self, workflow_def):
        # 判断工作流是否由触发器启动
        # 实现略，需根据实际需求编写
        pass

```

## 4. **执行引擎的分支处理**

### 4.1 动态执行路径

执行引擎不再预先计算执行顺序，而是在运行时根据节点的执行结果和边上的条件动态决定下一步执行的节点。

### 4.2 `_get_next_node_id` 方法

根据当前节点的输出和边上的条件，决定下一个要执行的节点。

```python
def _get_next_node_id(self, current_node_id, result, edges):
    outputs = result.get("__output__")
    for edge in edges:
        if edge["from"] == current_node_id:
            condition = edge.get("condition")
            if condition:
                if condition == outputs:
                    return edge["to"]
            else:
                # 默认连接
                return edge["to"]
    return None  # 无后续节点，结束

```

### 4.3 分支节点的处理

- *IfNode：**根据条件返回 `"true"` 或 `"false"`，执行引擎根据输出选择对应的分支。
- *SwitchNode：**根据变量的值返回相应的输出，执行引擎匹配 `condition` 选择对应的后续节点。

## 5. **配置验证和错误处理**

- 在节点类中定义 `config_schema`，使用 `pydantic` 验证配置。
- 在 `_create_node` 方法中捕获配置验证错误，提供详细的错误信息，方便调试和修改。

## 6. **使用示例**

```python
import asyncio

async def main():
    # 创建并启动引擎
    engine = WorkflowEngine()
    await engine.start()

    # 新增工作流
    workflow_def = {
        "id": "workflow_1",
        "nodes": [...],
        "edges": [...]
    }
    engine.storage.save_workflow(workflow_def)

    # 手动执行工作流
    await engine.workflow_runner.execute_workflow("workflow_1", {"data": {"amount": 1500}})

    # 停止引擎
    await engine.stop()

asyncio.run(main())

```

## 7. **改进的特点**

- *标准化术语：**使用 `nodes` 和 `edges`，符合图结构的标准表示。
- *配置验证：**每个节点都定义了配置模式，确保配置的正确性。
- *动态执行路径：**执行引擎能够处理条件分支和多路分支，适应复杂的工作流需求。
- *插件机制：**通过 `NodeRegistry`，方便添加新的节点类型，增强可扩展性。
- *异步执行：**使用 `asyncio` 实现异步执行，提高性能。

## 8. **未来扩展方向**

- *持久化存储：**实现 `WorkflowStorage` 的持久化逻辑，支持数据库或文件系统。
- *日志和监控：**添加日志记录和监控机制，方便运维和问题排查。
- *错误重试机制：**在节点执行失败时，支持重试策略，提升系统可靠性。
- *并发执行：**支持节点的并发执行，提升工作流的执行效率。
- *配置管理：**将配置与代码分离，使用配置文件或环境变量，提升灵活性。

## 9. **总结**

通过以上设计，工作流引擎具备了清晰的结构和良好的可扩展性，能够处理复杂的工作流逻辑，并为未来的功能扩展提供了良好的基础。

---

# Workflow Engine Design

## 1. **Core Components**

```
WorkflowEngine (Main Entry Point)
├── WorkflowRunner (Execution Engine)
├── WorkflowStorage (Storage Engine)
└── TriggerManager (Trigger Manager)

```

## 2. **Data Structures**

### 2.1 Nodes and Edges

The workflow is represented as a graph structure, where:

- **Nodes:** Represent individual operational units within the workflow, such as triggers, condition checks, HTTP requests, etc.
- **Edges:** Represent the connections and execution order between nodes, including conditional branching information.

### 2.2 Workflow Definition Example

```json
{
    "id": "workflow_1",
    "name": "Sample Workflow",
    "nodes": [
        {
            "id": "node_1",
            "type": "webhook",  // Trigger node
            "config": {
                "path": "/webhook/123",
                "method": "POST"
            }
        },
        {
            "id": "node_2",
            "type": "if",
            "config": {
                "condition": "data.amount > 1000"
            }
        },
        {
            "id": "node_3",
            "type": "action",
            "config": {
                "action_name": "approve"
            }
        },
        {
            "id": "node_4",
            "type": "action",
            "config": {
                "action_name": "reject"
            }
        }
    ],
    "edges": [
        {
            "from": "node_1",
            "to": "node_2"
        },
        {
            "from": "node_2",
            "to": "node_3",
            "condition": "true"
        },
        {
            "from": "node_2",
            "to": "node_4",
            "condition": "false"
        }
    ]
}

```

## 3. **Core Classes**

### 3.1 Node Registry

```python
class NodeRegistry:
    _registry = {}

    @classmethod
    def register(cls, node_type):
        def wrapper(node_class):
            cls._registry[node_type] = node_class
            return node_class
        return wrapper

    @classmethod
    def get_node_class(cls, node_type):
        return cls._registry.get(node_type)

```

### 3.2 Node Configuration Validation

Utilize the `pydantic` library for configuration validation.

```python
from pydantic import BaseModel, ValidationError

# Base node configuration model
class BaseNodeConfig(BaseModel):
    pass

# Base node class
class BaseNode:
    config_schema = BaseNodeConfig

    def __init__(self, config: dict):
        try:
            self.config = self.config_schema(**config)
        except ValidationError as e:
            errors = e.errors()
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in errors]
            error_str = "; ".join(error_messages)
            raise ValueError(f"Configuration validation failed: {error_str}")

    async def execute(self, input_data: dict) -> dict:
        raise NotImplementedError()

```

### 3.3 Node Type Definitions

### 3.3.1 IfNode (Conditional Node)

```python
@NodeRegistry.register("if")
class IfNode(BaseNode):
    class ConfigSchema(BaseNodeConfig):
        condition: str

    config_schema = ConfigSchema

    async def execute(self, input_data: dict) -> dict:
        condition = self.config.condition
        result = eval(condition, {}, input_data)
        output_key = "true" if result else "false"
        return {"__output__": output_key}

```

### 3.3.2 SwitchNode (Multi-way Branch Node)

```python
@NodeRegistry.register("switch")
class SwitchNode(BaseNode):
    class ConfigSchema(BaseNodeConfig):
        variable: str
        cases: list

    config_schema = ConfigSchema

    async def execute(self, input_data: dict) -> dict:
        variable_name = self.config.variable
        cases = self.config.cases
        value = eval(variable_name, {}, input_data)
        output_key = str(value) if value in cases else "default"
        return {"__output__": output_key}

```

### 3.3.3 Other Nodes

Other nodes are defined similarly and registered in the `NodeRegistry`.

### 3.4 Workflow Storage

```python
class WorkflowStorage:
    def save_workflow(self, workflow_def: dict):
        """Save the workflow definition to a database or file system"""
        pass

    def load_workflow(self, workflow_id: str) -> dict:
        """Load the workflow definition from a database or file system"""
        pass

    def list_workflows(self) -> list:
        """List all saved workflows"""
        pass

```

### 3.5 Trigger Manager

```python
class TriggerManager:
    def __init__(self):
        self.triggers = {}  # workflow_id -> trigger_node
        self.workflow_runner = None

    def set_workflow_runner(self, runner):
        self.workflow_runner = runner

    async def add_trigger(self, workflow_id: str, trigger_node: BaseNode):
        """Register a trigger"""
        self.triggers[workflow_id] = trigger_node
        await trigger_node.activate()

    async def remove_trigger(self, workflow_id: str):
        """Remove a trigger"""
        if workflow_id in self.triggers:
            await self.triggers[workflow_id].deactivate()
            del self.triggers[workflow_id]

    async def on_trigger(self, workflow_id: str, trigger_data: dict):
        """Called when a trigger is activated"""
        if self.workflow_runner:
            await self.workflow_runner.execute_workflow(workflow_id, trigger_data)

```

### 3.6 Workflow Runner (Execution Engine)

```python
class WorkflowRunner:
    def __init__(self):
        self.storage = WorkflowStorage()

    async def _create_node(self, node_def: dict) -> BaseNode:
        node_type = node_def["type"]
        node_class = NodeRegistry.get_node_class(node_type)
        if not node_class:
            raise ValueError(f"Unknown node type: {node_type}")

        try:
            node_instance = node_class(config=node_def.get("config", {}))
            return node_instance
        except ValueError as e:
            raise ValueError(f"Invalid configuration for node '{node_def['id']}': {e}")

    async def execute_workflow(self, workflow_id: str, trigger_data: dict = None):
        try:
            workflow_def = self.storage.load_workflow(workflow_id)
            nodes = {}
            for node_def in workflow_def["nodes"]:
                nodes[node_def["id"]] = await self._create_node(node_def)

            edges = workflow_def["edges"]
            node_results = {}
            # Initialize current node
            if trigger_data:
                current_node_id = workflow_def["nodes"][0]["id"]
                node_results[current_node_id] = trigger_data
            else:
                current_node_id = workflow_def["nodes"][0]["id"]

            # Dynamically execute nodes
            while current_node_id:
                current_node = nodes[current_node_id]
                input_data = self._get_node_input(current_node_id, edges, node_results)
                result = await current_node.execute(input_data)
                node_results[current_node_id] = result
                # Determine the next node based on execution result
                current_node_id = self._get_next_node_id(current_node_id, result, edges)

            return node_results
        except Exception as e:
            print(f"Error executing workflow: {e}")

    def _get_node_input(self, node_id, edges, node_results):
        # Retrieve input data for the node
        # Implementation needed based on actual requirements
        pass

    def _get_next_node_id(self, current_node_id, result, edges):
        outputs = result.get("__output__")
        for edge in edges:
            if edge["from"] == current_node_id:
                condition = edge.get("condition")
                if condition:
                    if condition == outputs:
                        return edge["to"]
                else:
                    # Default connection
                    return edge["to"]
        return None  # No further nodes, end execution

```

### 3.7 Workflow Engine

```python
class WorkflowEngine:
    def __init__(self):
        self.storage = WorkflowStorage()
        self.trigger_manager = TriggerManager()
        self.workflow_runner = WorkflowRunner()

        # Set mutual references
        self.trigger_manager.set_workflow_runner(self.workflow_runner)

    async def start(self):
        """Start the engine"""
        # Load all workflows
        workflows = self.storage.list_workflows()

        # Register triggers
        for workflow_def in workflows:
            if self._is_triggered_workflow(workflow_def):
                trigger_node = await self.workflow_runner._create_node(workflow_def["nodes"][0])
                await self.trigger_manager.add_trigger(workflow_def["id"], trigger_node)

    async def stop(self):
        """Stop the engine"""
        # Stop all triggers
        for workflow_id in list(self.trigger_manager.triggers.keys()):
            await self.trigger_manager.remove_trigger(workflow_id)

    def _is_triggered_workflow(self, workflow_def):
        # Determine if the workflow is initiated by a trigger
        # Implementation needed based on actual requirements
        pass

```

## 4. **Execution Engine's Branch Handling**

### 4.1 Dynamic Execution Path

The execution engine no longer precomputes the execution order but dynamically decides the next node to execute at runtime based on the execution results and the conditions specified on the edges.

### 4.2 `_get_next_node_id` Method

Determines the next node to execute based on the current node's output and the conditions on the edges.

```python
def _get_next_node_id(self, current_node_id, result, edges):
    outputs = result.get("__output__")
    for edge in edges:
        if edge["from"] == current_node_id:
            condition = edge.get("condition")
            if condition:
                if condition == outputs:
                    return edge["to"]
            else:
                # Default connection
                return edge["to"]
    return None  # No further nodes, end execution

```

### 4.3 Handling Branch Nodes

- **IfNode:** Returns `"true"` or `"false"` based on the condition; the execution engine selects the corresponding branch based on the output.
- **SwitchNode:** Returns the value of a variable; the execution engine matches the `condition` to select the next node to execute.

## 5. **Configuration Validation and Error Handling**

- Each node class defines a `config_schema` and uses `pydantic` to validate configurations.
- In the `_create_node` method, configuration validation errors are caught, providing detailed error information to facilitate debugging and correction.

## 6. **Usage Example**

```python
import asyncio

async def main():
    # Create and start the engine
    engine = WorkflowEngine()
    await engine.start()

    # Add a new workflow
    workflow_def = {
        "id": "workflow_1",
        "nodes": [...],
        "edges": [...]
    }
    engine.storage.save_workflow(workflow_def)

    # Manually execute a workflow
    await engine.workflow_runner.execute_workflow("workflow_1", {"data": {"amount": 1500}})

    # Stop the engine
    await engine.stop()

asyncio.run(main())

```

## 7. **Improved Features**

- **Standardized Terminology:** Uses `nodes` and `edges`, conforming to standard graph representations.
- **Configuration Validation:** Each node defines a schema for its configuration, ensuring correctness.
- **Dynamic Execution Path:** The execution engine can handle conditional and multi-way branches, adapting to complex workflow requirements.
- **Plugin Mechanism:** Through `NodeRegistry`, new node types can be easily added, enhancing extensibility.
- **Asynchronous Execution:** Uses `asyncio` for asynchronous execution, improving performance.

## 8. **Future Expansion Directions**

- **Persistent Storage:** Implement the persistence logic in `WorkflowStorage`, supporting databases or file systems.
- **Logging and Monitoring:** Add logging and monitoring mechanisms for easier maintenance and troubleshooting.
- **Error Retry Mechanism:** Support retry strategies when node execution fails, enhancing system reliability.
- **Concurrent Execution:** Support concurrent execution of nodes to improve workflow execution efficiency.
- **Configuration Management:** Separate configurations from code, using configuration files or environment variables for greater flexibility.

## 9. **Summary**

This design provides a clear structure and good extensibility for the workflow engine, capable of handling complex workflow logic and laying a solid foundation for future feature enhancements.