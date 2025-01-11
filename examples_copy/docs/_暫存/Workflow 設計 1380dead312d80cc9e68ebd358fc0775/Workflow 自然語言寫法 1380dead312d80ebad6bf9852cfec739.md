# Workflow 自然語言寫法

```markdown
Flow Creation Process
---

Tools available:
- `ask-user`: Ask user questions to gather information
- `ask-user-approve`: Get user's approval for the flow design
- `run-flow`: Execute and test the flow
- `create-task`: Create the final task with its tested flow

Process:
1. Agent receives a Task Creation request from user and analyzes what needs to be done
   - User explains what task they want to create
   - Agent analyzes requirements for both task and flow

2. If anything is unclear, agent uses `ask-user` to understand:
   - What are we trying to achieve?
   - What are the key steps needed?
   - What conditions or special cases should be handled?

3. Once clear, agent creates both:
   - Task description: Clear definition of what needs to be done
   - Flow design: Step-by-step process to accomplish the task
   Then explains both to user.

4. Agent uses `ask-user-approve` to get user's feedback:
   - If user wants changes, agent updates task/flow
   - If user approves, move to testing

5. Agent generates the flow in JSON format and uses `run-flow` to test it:
   - If it fails, agent fixes issues and tests again
   - If it succeeds, proceed to task creation

6. Agent uses `create-task` to formally create the task with its tested flow

7. Agent confirms successful task creation to user and provides:
   - Task ID or reference
   - Task description
   - Flow details
   - Any special notes or instructions
```

### 格式

1. 使用 [Type:SubType] 標記節點類型
2. 使用編號和縮進表示層級
3. 用 {var} 表示變量
4. 重要細節用縮進列點說明

### 主要 Node Types

基礎類型：

- [Trigger:Webhook]
- [Trigger:Schedule]
- [Trigger:Event]
- [Action:HTTP]
- [Action:DB]
- [Action:Email]

流程控制：

- [Branch] - 條件分支
- [Loop] - 循環
- [SubWorkflow] - 子流程

整合類型：

- [Action:Github]
- [Action:Slack]
- [Action:Jira]
- [Action:Notion]

AI 類型：

- [AI:ChatGPT]
- [AI:Claude]

範例

```markdown
# [Flow] Prompt to Task

1. [Trigger:Input] Receive task description from user

2. [AI:Claude] Generate task proposal
   - Parse user input to extract:
     * Core objectives
     * Expected deliverables
     * Timeline hints
     * Resource requirements
   - Search existing projects for potential matches
   - Generate structured proposal:
     * Task title & description
     * Estimated timeline
     * Required resources
     * Suggested tags
     * Project association (if applicable)
     * Draft workflow steps

3. [Human:Review] Review task proposal
   - Review and provide feedback
   - Can request modifications on any aspect
   
4. [Loop:Refinement] Until user approves
   1. [AI:Claude] Adjust task based on feedback
   2. [Human:Review] Review changes
   - Exit condition: User approves task

5. [AI:Claude] Generate execution workflow
   - Design detailed execution steps
   - Define checkpoints and reviews
   - Specify step executors (Human/AI/System)

6. [Human:Review] Review workflow
   - Review and provide feedback
   - Can request workflow adjustments

7. [Loop:WorkflowTest] Until workflow validated
   1. [Action:System] Simulate workflow execution
   2. [AI:Claude] Analyze simulation results
   3. [AI:Claude] Suggest workflow improvements
   4. [Human:Review] Review simulation results
   - Exit condition: Workflow passes validation

8. [Action:DB] Create task record
   - Store final task details
   - Store approved workflow
   - Mark task as ready for execution

Notes:
- Each [Human:Review] step can trigger a return to the previous major step
- Simulation helps identify potential issues before actual execution
- Task is only created after both task details and workflow are approved
```

```markdown
# Github Issue Handler

1. [Trigger:Webhook] Github new issue created
2. [Action:Github] Get issue details from API
3. [Branch] Check if issue has "bug" label
   - If true:
     1. [Action:Slack] Send to dev-team: "New Bug: {issue title}"
     2. [Action:Jira] Create ticket with issue details
   - If false:
     1. [Action:Github] Add "feature-request" label
     2. [Action:Slack] Send to product-team: "New Feature: {issue title}"
4. [AI:ChatGPT] Analyze issue content
   - Prompt: Analyze issue and generate helpful response
   - Context: issue title, body, and labels
5. [Action:Github] Post AI response as comment

# Weekly Report Generator

1. [Trigger:Schedule] Every Monday at 9am
2. [Action:DB] Get list of active products
3. [Loop] For each product:
   1. [Action:Analytics] Get last week's metrics (DAU, revenue, conversion)
   2. [AI:Claude] Analyze metrics and generate insights
      - Focus on: trends, changes, issues, recommendations
   3. [Action:DB] Save product analysis
4. [Action:DB] Merge all product reports
5. [Action:Email] Send weekly report to team
```

```markdown
# 1. Task Creation Flow

1. [Trigger:Event] New task request received
2. [AI:Claude] Initial task analysis
   - Parse request description
   - Identify task type and category
   - Extract key requirements
   - Detect related tasks/projects
3. [AI:Claude] Generate task structure
   - Title and description
   - Estimated effort/timeline
   - Required resources
   - Suggested tags
4. [Branch] Check if part of existing project
   - If yes:
     1. [Action:DB] Fetch project context
     2. [AI:Claude] Analyze project fit
     3. [AI:Claude] Adjust priority based on project
   - If no:
     1. [AI:Claude] Suggest project creation
5. [Human] Review and adjust task details
6. [Action:DB] Create task record
7. [SubWorkflow] Generate task workflow
   1. [AI:Claude] Design execution steps
   2. [AI:Claude] Identify required reviews/checkpoints
   3. [Action:DB] Create workflow steps
8. [Action:Notify] Inform relevant team members
9. [Action:DB] Update task trackers

# 2. Project Creation Flow

1. [Trigger:Event] New project request received
2. [AI:Claude] Project analysis
   - Parse project description
   - Identify project scope
   - Extract key objectives
   - Analyze resource requirements
3. [AI:Claude] Generate project structure
   - Project overview
   - Goals and success metrics
   - Timeline estimation
   - Resource allocation plan
4. [SubWorkflow] Initial task breakdown
   1. [AI:Claude] Identify major components
   2. [AI:Claude] Create high-level tasks
   3. [AI:Claude] Define dependencies
5. [Human] Review and adjust project plan
6. [Action:DB] Create project record
7. [SubWorkflow] Setup project infrastructure
   1. [Action:Github] Create repository
   2. [Action:Notion] Create project docs
   3. [Action:Slack] Create project channel
8. [AI:Claude] Generate project timeline
   - Milestone planning
   - Resource scheduling
   - Risk assessment
9. [Action:DB] Initialize project trackers
10. [Action:Notify] Inform stakeholders

# 3. App Feature Planning Flow

1. [Trigger:Event] Feature planning requested
2. [AI:Claude] Market research
   - Analyze competitor features
   - Review user feedback/requests
   - Identify market trends
   - Research technical feasibility
3. [SubWorkflow] User need analysis
   1. [Action:DB] Fetch user feedback data
   2. [AI:Claude] Analyze pain points
   3. [AI:Claude] Identify user patterns
4. [AI:Claude] Generate feature proposals
   - Core functionality
   - User interface design
   - Technical requirements
   - Implementation approach
5. [Human] Review and select features
6. [AI:Claude] Detailed feature planning
   - User stories
   - Technical specifications
   - API requirements
   - Database schema changes
7. [Branch] Based on feature scope
   - If major feature:
     1. [SubWorkflow] Create feature project
     2. [Action:DB] Set major milestone
   - If minor feature:
     1. [Action:DB] Create feature task
8. [SubWorkflow] Resource planning
   1. [AI:Claude] Estimate development effort
   2. [AI:Claude] Identify required skills
   3. [Action:DB] Check resource availability
9. [Action:Notify] Share feature plan
10. [Action:DB] Update product roadmap

# 4. MVP Development Flow

1. [Trigger:Event] Start MVP development
2. [SubWorkflow] Setup development environment
   1. [Action:Github] Initialize repository
   2. [Action:DevOps] Setup CI/CD pipeline
   3. [Action:DB] Configure development database
3. [AI:Claude] Generate technical design
   - Architecture overview
   - Component design
   - API specifications
   - Database schema
4. [SubWorkflow] Task breakdown
   1. [AI:Claude] Create development tasks
   2. [AI:Claude] Set task dependencies
   3. [Action:DB] Create sprint plan
5. [Loop] Development sprints
   1. [SubWorkflow] Sprint planning
      - Task prioritization
      - Resource allocation
      - Timeline setting
   2. [SubWorkflow] Development
      - Code implementation
      - Code review
      - Testing
   3. [SubWorkflow] Sprint review
      - Progress tracking
      - Quality check
      - Feedback collection
6. [Branch] Feature completion check
   - If incomplete:
     1. [AI:Claude] Adjust sprint plan
     2. [Action:DB] Update timeline
   - If complete:
     1. [SubWorkflow] Testing
     2. [SubWorkflow] Documentation
     3. [Action:Github] Prepare release
7. [Human] Final MVP review
8. [SubWorkflow] MVP deployment
   1. [Action:DevOps] Deploy to production
   2. [Action:Monitor] Setup monitoring
   3. [Action:DB] Update version tracking
9. [Action:Notify] Announce MVP completion
```