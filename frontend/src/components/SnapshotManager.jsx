import React, { useState } from 'react';
import { Save, Trash2, Copy, Download } from 'lucide-react';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Input } from './ui/input';

const SnapshotManager = ({ snapshots, onSave, onDelete, onLoad, onExportText, deadlines, manualPlan }) => {
  const [saveName, setSaveName] = useState('');
  const [isSaveOpen, setIsSaveOpen] = useState(false);
  const [isListOpen, setIsListOpen] = useState(false);
  const [copiedId, setCopiedId] = useState(null);

  const handleSave = () => {
    onSave(saveName, deadlines, manualPlan);
    setSaveName('');
    setIsSaveOpen(false);
  };

  const handleCopy = (snapshot) => {
    const text = onExportText(snapshot);
    navigator.clipboard.writeText(text);
    setCopiedId(snapshot.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex items-center gap-2">
      {/* Save Snapshot */}
      <Dialog open={isSaveOpen} onOpenChange={setIsSaveOpen}>
        <DialogTrigger asChild>
          <Button
            size="sm"
            className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs h-8"
          >
            <Save className="w-3.5 h-3.5 mr-1.5" />
            Save Snapshot
          </Button>
        </DialogTrigger>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-slate-800 dark:text-slate-100">Save Snapshot</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-2">
            <Input
              value={saveName}
              onChange={(e) => setSaveName(e.target.value)}
              placeholder="Snapshot name (optional)"
              onKeyDown={(e) => e.key === 'Enter' && handleSave()}
              autoFocus
            />
            <Button onClick={handleSave} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white">
              Save
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* View Snapshots */}
      {snapshots.length > 0 && (
        <Dialog open={isListOpen} onOpenChange={setIsListOpen}>
          <DialogTrigger asChild>
            <Button
              size="sm"
              variant="outline"
              className="text-xs h-8 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300"
            >
              <Download className="w-3.5 h-3.5 mr-1.5" />
              Snapshots ({snapshots.length})
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md max-h-[70vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-slate-800 dark:text-slate-100">Saved Snapshots</DialogTitle>
            </DialogHeader>
            <div className="space-y-2 mt-2">
              {snapshots.map((snapshot) => (
                <div
                  key={snapshot.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-700 dark:text-slate-200 truncate">
                      {snapshot.name}
                    </p>
                    <p className="text-[10px] text-slate-500 dark:text-slate-400">
                      {new Date(snapshot.createdAt).toLocaleString()} &middot; {snapshot.deadlines.filter(d => d.daysNeeded).length} planned
                    </p>
                  </div>
                  <div className="flex items-center gap-1 ml-2 shrink-0">
                    <Button
                      size="icon"
                      variant="ghost"
                      className="w-7 h-7 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30"
                      onClick={() => {
                        onLoad(snapshot);
                        setIsListOpen(false);
                      }}
                      title="Load"
                    >
                      <Download className="w-3.5 h-3.5" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="w-7 h-7 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
                      onClick={() => handleCopy(snapshot)}
                      title="Copy as text"
                    >
                      {copiedId === snapshot.id ? (
                        <span className="text-[10px] text-emerald-600">OK</span>
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="w-7 h-7 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30"
                      onClick={() => onDelete(snapshot.id)}
                      title="Delete"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

export default SnapshotManager;
