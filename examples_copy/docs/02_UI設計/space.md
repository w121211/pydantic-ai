# Space

直接使用 user 本機的資料夾，方變 user 用不同的方式來做修改

```
# directory structure

project_name
- task_21-hello_world
  - works
    - remote_direcoty_1
      - ...
    - remote_direcoty_2
  - subtask_0-Planning
    - step_0_1-Planning
      - output-work_plan_20241010
      - subtask.lock
    - step_0_2-Planning
  - step_1-a_sample_step
    - chat_20241023_xxxx.txt
    - chat_20241023_0921.txt
    - work-goodbye_world_20241023_0921.py
    - work-hello_world_20241023_0921.py
    - work-hello_world_20241023_0928.py
  - step_2-...
    - ...
  - step_3-...
    - ...
  - step_4-... # 只有已經執行到的 step 會創建 folder，尚未執行到的step沒有folder
  - task.lock  # task 以此為準，刪掉會嘗試從 step_0/output 重新創建
- task_20-hello_world
  - ...
- ...
- (一個問題是當累積太多時，UI可能會需要隱藏部分 tasks，例如只展示當前在進行的)
```

subtask (step) folder
- 若被刪除
  - case: 正在執行的 subtask folder -> 無法寫入，產生 error
  - case: 已經執行完畢的 subtask folder -> 除非重跑 task，不然不會自動建立
    - task 執行狀態是依照 task.lock 所以刪掉 subtask folder 並不會影響 task
    - 因為沒有 subtask folder，所以無法重新執行這的 subtask
- 重新執行
  - 依照 folder 中的 input (或不需要 input)，重跑 subtask
  - 
  - 



```
# UI view: project navigator

專案：AI App    [⋮] [➕]
⌄ #12 首頁 UI 開發 🏃
  ⌄ _resource
    - 📄 any_file.py
    - plan.txt
  > _or_any_folder_put_in_this_directory
  ⌄ Step 0: Planning [+新對話] [RUN]
    - plan
  ⌄ Step 1: 定義需求 [+新對話] [RUN]
    - _input.json  # step 的輸入資料
    - 💬 chat_20241023_0921.json [clone]
    - 💬 chat_20241023_0921.json
    - 💬 you_can_rename_the_chat.json
    - 📄 you_can_rename_the_file.py
    - 📄 or_create_any_file.py
    - 📄 hello_world_20241023_0921.py
    - 📄 hello_world_20241023_0920.py
  > (Step running icon) 分析 UI/UX
  > (Step wait to run icon) ...

> #11 任務名 (執行狀態)
> #10 任務名 (執行狀態)
- [展開已經完成、終止的任務]
```
