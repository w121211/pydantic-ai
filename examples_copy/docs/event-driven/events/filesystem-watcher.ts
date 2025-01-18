import { EventEmitter } from 'events';
import { Task } from './types';

export type FileSystemEvent = {
  type: 'add' | 'change' | 'unlink' | 'addDir' | 'unlinkDir';
  path: string;
};

export class FileSystemWatcher extends EventEmitter {
  private watcherId: number | null = null;
  private tasks: Map<string, Task> = new Map();

  constructor(private workspacePath: string) {
    super();
  }

  async initialize() {
    // Initialize the watcher
    try {
      // In a real implementation, this would use the platform's file system watching capabilities
      // For browser environments, this might involve WebSocket connections to a backend
      this.watcherId = window.fs.watch(this.workspacePath, { recursive: true }, 
        (eventType: string, filename: string) => {
          this.handleFileChange(eventType, filename);
      });
    } catch (error) {
      console.error('Failed to initialize file system watcher:', error);
      throw error;
    }
  }

  private async handleFileChange(eventType: string, filename: string) {
    const event: FileSystemEvent = {
      type: this.mapEventType(eventType),
      path: filename,
    };

    // Emit the event for subscribers to handle
    this.emit('change', event);

    // If this is a task.lock file change, update our task cache
    if (filename.endsWith('task.lock')) {
      try {
        const content = await window.fs.readFile(filename, { encoding: 'utf8' });
        const task = JSON.parse(content);
        this.tasks.set(task.id, task);
        this.emit('taskUpdate', task);
      } catch (error) {
        console.error('Failed to process task.lock update:', error);
      }
    }
  }

  private mapEventType(eventType: string): FileSystemEvent['type'] {
    switch (eventType) {
      case 'rename':
        return 'unlink'; // This needs more sophisticated detection
      case 'change':
        return 'change';
      default:
        return 'change';
    }
  }

  stop() {
    if (this.watcherId !== null) {
      window.fs.unwatch(this.watcherId);
      this.watcherId = null;
    }
  }

  getTask(taskId: string): Task | undefined {
    return this.tasks.get(taskId);
  }

  getAllTasks(): Task[] {
    return Array.from(this.tasks.values());
  }
}

// Utility function to convert file system events to FileNode updates
export function processFileSystemEvent(
  event: FileSystemEvent,
  currentTree: FileNode[]
): FileNode[] {
  const { type, path } = event;
  
  switch (type) {
    case 'unlink':
    case 'unlinkDir':
      return removeNodeByPath(currentTree, path);
    case 'add':
    case 'addDir':
      return addNodeByPath(currentTree, path);
    case 'change':
      return updateNodeByPath(currentTree, path);
    default:
      return currentTree;
  }
}

// Helper functions for tree manipulation
function removeNodeByPath(tree: FileNode[], path: string): FileNode[] {
  return tree.filter(node => {
    if (node.path === path) return false;
    if (node.children) {
      node.children = removeNodeByPath(node.children, path);
    }
    return true;
  });
}

function addNodeByPath(tree: FileNode[], path: string): FileNode[] {
  // Implementation would depend on how we want to handle new files
  // This is a simplified version
  const parts = path.split('/');
  const name = parts[parts.length - 1];
  
  if (parts.length === 1) {
    return [...tree, {
      name,
      path,
      type: path.includes('.') ? 'file' : 'directory',
      children: [],
    }];
  }
  
  return tree.map(node => {
    if (node.path === parts[0]) {
      return {
        ...node,
        children: addNodeByPath(node.children || [], parts.slice(1).join('/')),
      };
    }
    return node;
  });
}

function updateNodeByPath(tree: FileNode[], path: string): FileNode[] {
  // Implementation for updating node metadata
  return tree.map(node => {
    if (node.path === path) {
      return {
        ...node,
        // Update relevant properties
      };
    }
    if (node.children) {
      return {
        ...node,
        children: updateNodeByPath(node.children, path),
      };
    }
    return node;
  });
}