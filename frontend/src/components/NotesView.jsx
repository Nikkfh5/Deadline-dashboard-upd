import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Plus, Trash2, Check, X, GripVertical, LayoutGrid, List } from 'lucide-react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { fetchNotes, createNoteApi, updateNoteApi, deleteNoteApi, reorderNotesApi } from '../services/api';
import { useViewMode } from '../hooks/useViewMode';
import CanvasView from './CanvasView';

function NoteCard({ note, onUpdate, onDelete, compact = false }) {
  const [editing, setEditing] = useState(false);
  const [titleVal, setTitleVal] = useState(note.title || '');
  const [contentVal, setContentVal] = useState(note.content || '');
  const textareaRef = useRef(null);

  useEffect(() => {
    if (editing && textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.selectionStart = textareaRef.current.value.length;
    }
  }, [editing]);

  const save = async () => {
    await onUpdate(note.id, {
      title: titleVal.trim() || null,
      content: contentVal,
    });
    setEditing(false);
  };

  const cancel = () => {
    setTitleVal(note.title || '');
    setContentVal(note.content || '');
    setEditing(false);
  };

  if (compact) {
    return (
      <div
        className="w-52 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-3 shadow-sm select-none"
        onDoubleClick={() => setEditing(true)}
      >
        {note.title && (
          <p className="text-xs font-semibold text-slate-700 dark:text-slate-200 mb-1 truncate">{note.title}</p>
        )}
        <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-3 whitespace-pre-wrap break-words">
          {note.content || <span className="italic text-slate-300 dark:text-slate-600">Пусто</span>}
        </p>
      </div>
    );
  }

  return (
    <div className="group relative bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
      {editing ? (
        <div className="flex flex-col gap-2">
          <input
            value={titleVal}
            onChange={e => setTitleVal(e.target.value)}
            placeholder="Заголовок (опционально)"
            className="text-sm font-semibold bg-transparent border-b border-slate-200 dark:border-slate-700 outline-none text-slate-700 dark:text-slate-200 pb-1"
          />
          <textarea
            ref={textareaRef}
            value={contentVal}
            onChange={e => setContentVal(e.target.value)}
            rows={5}
            placeholder="Содержимое..."
            className="text-sm bg-transparent outline-none resize-none text-slate-600 dark:text-slate-300 placeholder:text-slate-400"
          />
          <div className="flex justify-end gap-2">
            <button onClick={cancel} className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600">
              <X className="w-3 h-3" /> Отмена
            </button>
            <button onClick={save} className="flex items-center gap-1 text-xs text-emerald-600 hover:text-emerald-700 font-medium">
              <Check className="w-3 h-3" /> Сохранить
            </button>
          </div>
        </div>
      ) : (
        <div onClick={() => setEditing(true)} className="cursor-text min-h-[60px]">
          {note.title && (
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-1">{note.title}</p>
          )}
          <p className="text-sm text-slate-500 dark:text-slate-400 whitespace-pre-wrap break-words">
            {note.content || <span className="italic text-slate-300 dark:text-slate-500">Нажмите чтобы редактировать...</span>}
          </p>
        </div>
      )}

      {!editing && (
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(note.id); }}
          className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1 rounded text-slate-300 dark:text-slate-600 hover:text-rose-500 dark:hover:text-rose-400 transition-all"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}

function SortableNote({ note, onUpdate, onDelete }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: note.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className="flex items-start gap-2">
      <button
        {...attributes}
        {...listeners}
        className="mt-3 p-1 text-slate-300 dark:text-slate-600 hover:text-slate-500 dark:hover:text-slate-400 cursor-grab active:cursor-grabbing flex-shrink-0"
      >
        <GripVertical className="w-4 h-4" />
      </button>
      <div className="flex-1">
        <NoteCard note={note} onUpdate={onUpdate} onDelete={onDelete} />
      </div>
    </div>
  );
}

function NewNoteInput({ onSubmit, onCancel }) {
  const [content, setContent] = useState('');
  const [title, setTitle] = useState('');
  const ref = useRef(null);

  useEffect(() => { ref.current?.focus(); }, []);

  const submit = async () => {
    if (!content.trim() && !title.trim()) { onCancel(); return; }
    await onSubmit({ title: title.trim() || null, content: content.trim() });
  };

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-xl p-4 shadow-sm">
      <input
        value={title}
        onChange={e => setTitle(e.target.value)}
        placeholder="Заголовок (опционально)"
        className="w-full text-sm font-semibold bg-transparent border-b border-slate-200 dark:border-slate-700 outline-none text-slate-700 dark:text-slate-200 pb-1 mb-2"
      />
      <textarea
        ref={ref}
        value={content}
        onChange={e => setContent(e.target.value)}
        onKeyDown={e => { if (e.key === 'Escape') onCancel(); }}
        rows={4}
        placeholder="Содержимое..."
        className="w-full text-sm bg-transparent outline-none resize-none text-slate-600 dark:text-slate-300 placeholder:text-slate-400"
      />
      <div className="flex justify-end gap-2 mt-2">
        <button onClick={onCancel} className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600">
          <X className="w-3 h-3" /> Отмена
        </button>
        <button onClick={submit} className="flex items-center gap-1 text-xs text-emerald-600 hover:text-emerald-700 font-medium">
          <Check className="w-3 h-3" /> Добавить
        </button>
      </div>
    </div>
  );
}

export default function NotesView({ folderId }) {
  const [notes, setNotes] = useState([]);
  const [creating, setCreating] = useState(false);
  const [activeId, setActiveId] = useState(null);
  const { viewMode, setViewMode, getPositions, savePosition, resetPositions } = useViewMode(folderId);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  useEffect(() => {
    if (!folderId) return;
    fetchNotes(folderId).then(data => { if (data) setNotes(data); });
  }, [folderId]);

  const handleCreate = async (data) => {
    setCreating(false);
    const note = await createNoteApi({ ...data, folder_id: folderId });
    if (note) setNotes(prev => [...prev, note]);
  };

  const handleUpdate = async (noteId, data) => {
    const updated = await updateNoteApi(noteId, data);
    if (updated) setNotes(prev => prev.map(n => n.id === noteId ? updated : n));
  };

  const handleDelete = async (noteId) => {
    await deleteNoteApi(noteId);
    setNotes(prev => prev.filter(n => n.id !== noteId));
  };

  const handleDragEnd = useCallback((event) => {
    const { active, over } = event;
    setActiveId(null);
    if (!over || active.id === over.id) return;
    setNotes(prev => {
      const oldIndex = prev.findIndex(n => n.id === active.id);
      const newIndex = prev.findIndex(n => n.id === over.id);
      const reordered = arrayMove(prev, oldIndex, newIndex).map((n, i) => ({ ...n, order: i }));
      reorderNotesApi(reordered.map(n => ({ id: n.id, order: n.order })));
      return reordered;
    });
  }, []);

  const activeNote = notes.find(n => n.id === activeId);

  return (
    <div>
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 dark:bg-slate-200 text-white dark:text-slate-900 text-sm font-medium hover:bg-slate-700 dark:hover:bg-slate-300 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Новая заметка
        </button>

        <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg">
          <button
            onClick={() => setViewMode('list')}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors ${
              viewMode === 'list'
                ? 'bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 shadow-sm'
                : 'text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300'
            }`}
          >
            <List className="w-3.5 h-3.5" />
            Список
          </button>
          <button
            onClick={() => setViewMode('canvas')}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors ${
              viewMode === 'canvas'
                ? 'bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 shadow-sm'
                : 'text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300'
            }`}
          >
            <LayoutGrid className="w-3.5 h-3.5" />
            Холст
          </button>
        </div>
      </div>

      {creating && (
        <div className="mb-4">
          <NewNoteInput onSubmit={handleCreate} onCancel={() => setCreating(false)} />
        </div>
      )}

      {notes.length === 0 && !creating && (
        <div className="text-center py-20 text-slate-400 dark:text-slate-600">
          <p className="text-sm">Пусто. Добавьте первую заметку.</p>
        </div>
      )}

      {viewMode === 'list' ? (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={({ active }) => setActiveId(active.id)}
          onDragEnd={handleDragEnd}
          onDragCancel={() => setActiveId(null)}
        >
          <SortableContext items={notes.map(n => n.id)} strategy={verticalListSortingStrategy}>
            <div className="flex flex-col gap-3 max-w-xl mx-auto">
              {notes.map(note => (
                <SortableNote
                  key={note.id}
                  note={note}
                  onUpdate={handleUpdate}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          </SortableContext>
          <DragOverlay>
            {activeNote && (
              <div className="opacity-80 rotate-1 shadow-xl">
                <NoteCard note={activeNote} onUpdate={() => {}} onDelete={() => {}} />
              </div>
            )}
          </DragOverlay>
        </DndContext>
      ) : (
        <CanvasView
          items={notes}
          getPositions={getPositions}
          savePosition={savePosition}
          onReset={resetPositions}
          renderCard={(note) => (
            <NoteCard
              note={note}
              onUpdate={handleUpdate}
              onDelete={handleDelete}
              compact
            />
          )}
        />
      )}
    </div>
  );
}
