
class RoundRobinChat {
    private participants: string[];
    private currentIndex: number;
    private eventEmitter: EventEmitter;
  
    constructor(participants: string[]) {
      this.participants = participants;
      this.currentIndex = 0;
      this.eventEmitter = new EventEmitter();
      
      // 初始化時觸發對話開始
      this.emit(Events.CONVERSATION_STARTED);
    }
  
    // Event 定義
    private Events = {
      MESSAGE_RECEIVED: 'messageReceived',
      MESSAGE_SENT: 'messageSent',
      TURN_STARTED: 'turnStarted',
      TURN_ENDED: 'turnEnded',
      ROUND_COMPLETED: 'roundCompleted',
      CONVERSATION_STARTED: 'conversationStarted',
      CONVERSATION_ENDED: 'conversationEnded'
    }
  
    // Turn 管理相關方法
    getCurrentParticipant(): string {
      return this.participants[this.currentIndex];
    }
  
    getNextParticipant(): string {
      const nextIndex = (this.currentIndex + 1) % this.participants.length;
      return this.participants[nextIndex];
    }
  
    private advanceTurn(): void {
      this.emit(Events.TURN_ENDED, this.getCurrentParticipant());
      
      this.currentIndex = (this.currentIndex + 1) % this.participants.length;
      
      if (this.currentIndex === 0) {
        this.emit(Events.ROUND_COMPLETED);
      }
      
      this.emit(Events.TURN_STARTED, this.getCurrentParticipant());
    }
  
    // 訊息處理方法
    async handleMessage(message: string, sender: string): Promise<void> {
      if (sender !== this.getCurrentParticipant()) {
        throw new Error('Not your turn to send message');
      }
  
      this.emit(Events.MESSAGE_RECEIVED, {
        content: message,
        sender,
        timestamp: new Date()
      });
  
      // 處理訊息並發送
      await this.processAndSendMessage(message);
      
      // 進入下一個回合
      this.advanceTurn();
    }
  
    private async processAndSendMessage(message: string): Promise<void> {
      // 處理訊息的邏輯
      this.emit(Events.MESSAGE_SENT, {
        content: message,
        sender: this.getCurrentParticipant(),
        nextParticipant: this.getNextParticipant(),
        timestamp: new Date()
      });
    }
  
    // Event 處理相關方法
    on(eventName: string, handler: Function): void {
      this.eventEmitter.on(eventName, handler);
    }
  
    private emit(eventName: string, data?: any): void {
      this.eventEmitter.emit(eventName, data);
    }
  
    // 結束對話
    end(): void {
      this.emit(Events.CONVERSATION_ENDED);
    }
  }
  
  // 使用範例
  const chat = new RoundRobinChat(['agentA', 'agentB', 'userC']);
  
  // 註冊事件監聽
  chat.on(Events.MESSAGE_RECEIVED, (message) => {
    console.log('Message received:', message);
  });
  
  chat.on(Events.TURN_STARTED, (participant) => {
    console.log(`${participant}'s turn started`);
  });
  
  // 發送訊息
  await chat.handleMessage('Hello', 'agentA');