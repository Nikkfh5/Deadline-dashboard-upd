import React, { useState, useRef, useEffect } from 'react';
import { Plus, MoreHorizontal, Pencil, Trash2, X, Check, FileText, Calendar } from 'lucide-react';

const TYPE_ICONS = {
  deadlines: Calendar,
  ideas: FileText,
};

function FolderTab({ folder, isActive, onClick, onRename, onDelete, canDelete }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
  const [renaming, setRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState(folder.name);
  const inputRef = useRef(null);
  const menuRef = useRef(null);
  const triggerRef = useRef(null);

  useEffect(() => {
    if (renaming) inputRef.current?.focus();
  }, [renaming]);

  useEffect(() => {
    if (!menuOpen) return;
    const close = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target) &&
          triggerRef.current && !triggerRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    const onScroll = () => setMenuOpen(false);
    document.addEventListener('mousedown', close);
    window.addEventListener('scroll', onScroll, true);
    return () => {
      document.removeEventListener('mousedown', close);
      window.removeEventListener('scroll', onScroll, true);
    };
  }, [menuOpen]);

  const openMenu = (e) => {
    e.stopPropagation();
    if (menuOpen) { setMenuOpen(false); return; }
    const rect = triggerRef.current?.getBoundingClientRect();
    if (rect) setMenuPos({ top: rect.bottom + 4, left: rect.left });
    setMenuOpen(true);
  };

  const commitRename = async () => {
    const trimmed = renameValue.trim();
    if (trimmed && trimmed !== folder.name) {
      await onRename(folder.id, trimmed);
    }
    setRenaming(false);
  };

  const Icon = TYPE_ICONS[folder.type] || FileText;

  return (
    <div className="relative group flex-shrink-0">
      <button
        onClick={onClick}
        className={`
          flex items-center gap-1.5 px-3 py-1.5 rounded-t-md text-sm font-medium
          border-b-2 transition-all duration-150 whitespace-nowrap
          ${isActive
            ? 'border-slate-700 dark:border-slate-200 text-slate-800 dark:text-slate-100 bg-white dark:bg-slate-800'
            : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:border-slate-300 dark:hover:border-slate-600'
          }
        `}
      >
        <Icon className="w-3.5 h-3.5 flex-shrink-0" />
        {renaming ? (
          <input
            ref={inputRef}
            value={renameValue}
            onChange={e => setRenameValue(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') commitRename();
              if (e.key === 'Escape') { setRenaming(false); setRenameValue(folder.name); }
            }}
            onBlur={commitRename}
            onClick={e => e.stopPropagation()}
            className="w-24 bg-transparent border-b border-slate-400 dark:border-slate-500 outline-none text-sm"
          />
        ) : (
          <span>{folder.name}</span>
        )}
      </button>

      {/* Context menu trigger — visible on hover/active */}
      <button
        ref={triggerRef}
        onClick={openMenu}
        className={`
          absolute right-0 top-1 flex items-center justify-center w-5 h-5 rounded
          transition-opacity duration-100
          text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300
          ${menuOpen ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}
        `}
      >
        <MoreHorizontal className="w-3 h-3" />
      </button>

      {menuOpen && (
        <div
          ref={menuRef}
          style={{ position: 'fixed', top: menuPos.top, left: menuPos.left, zIndex: 9999 }}
          className="min-w-[150px] bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl py-1"
        >
          <button
            onClick={() => { setMenuOpen(false); setRenaming(true); setRenameValue(folder.name); }}
            className="flex items-center gap-2 w-full px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"
          >
            <Pencil className="w-3.5 h-3.5" />
            Rename
          </button>
          <button
            onClick={() => { setMenuOpen(false); onDelete(folder.id); }}
            disabled={!canDelete}
            title={!canDelete ? 'Cannot delete the only deadlines folder' : undefined}
            className={`
              flex items-center gap-2 w-full px-3 py-1.5 text-sm
              ${canDelete
                ? 'text-rose-500 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30'
                : 'text-slate-300 dark:text-slate-600 cursor-not-allowed'
              }
            `}
          >
            <Trash2 className="w-3.5 h-3.5" />
            Delete
          </button>
        </div>
      )}
    </div>
  );
}

function NewFolderForm({ onSubmit, onCancel }) {
  const [name, setName] = useState('');
  const [type, setType] = useState('deadlines');
  const inputRef = useRef(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const submit = () => {
    const trimmed = name.trim();
    if (trimmed) onSubmit(trimmed, type);
  };

  return (
    <div className="flex items-center gap-1.5 px-2 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-sm">
      <select
        value={type}
        onChange={e => setType(e.target.value)}
        className="text-xs bg-transparent text-slate-500 dark:text-slate-400 border-none outline-none cursor-pointer"
      >
        <option value="deadlines">Deadlines</option>
        <option value="ideas">Ideas</option>
      </select>
      <input
        ref={inputRef}
        value={name}
        onChange={e => setName(e.target.value)}
        placeholder="Название..."
        onKeyDown={e => {
          if (e.key === 'Enter') submit();
          if (e.key === 'Escape') onCancel();
        }}
        className="w-28 text-sm bg-transparent outline-none text-slate-700 dark:text-slate-200 placeholder:text-slate-400"
      />
      <button
        onClick={submit}
        disabled={!name.trim()}
        className="text-emerald-500 hover:text-emerald-600 disabled:text-slate-300 dark:disabled:text-slate-600"
      >
        <Check className="w-3.5 h-3.5" />
      </button>
      <button onClick={onCancel} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

export default function FolderTabs({ folders, activeFolderId, onSwitch, onCreate, onRename, onDelete }) {
  const [creatingNew, setCreatingNew] = useState(false);

  const deadlinesFolderCount = folders.filter(f => f.type === 'deadlines').length;

  const handleCreate = async (name, type) => {
    setCreatingNew(false);
    await onCreate(name, type);
  };

  if (!folders.length) return null;

  return (
    <div className="flex items-end gap-0.5 border-b border-slate-200 dark:border-slate-700 mb-6 px-1 overflow-x-auto">
      {folders.map(folder => (
        <FolderTab
          key={folder.id}
          folder={folder}
          isActive={folder.id === activeFolderId}
          onClick={() => onSwitch(folder.id)}
          onRename={onRename}
          onDelete={onDelete}
          canDelete={!(folder.type === 'deadlines' && deadlinesFolderCount <= 1)}
        />
      ))}

      {creatingNew ? (
        <div className="mb-1 ml-1">
          <NewFolderForm onSubmit={handleCreate} onCancel={() => setCreatingNew(false)} />
        </div>
      ) : (
        <button
          onClick={() => setCreatingNew(true)}
          className="flex items-center justify-center w-7 h-7 mb-0.5 rounded-md text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors flex-shrink-0"
          title="Новая папка"
        >
          <Plus className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
