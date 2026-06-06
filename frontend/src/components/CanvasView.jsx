import React, { useState, useCallback, useRef } from 'react';
import { DndContext, useDraggable } from '@dnd-kit/core';
import { RotateCcw } from 'lucide-react';

const CARD_DEFAULT_W = 220;
const CARD_DEFAULT_H = 100;
const GRID_COLS = 4;
const GRID_GAP = 20;

function gridPosition(index) {
  const col = index % GRID_COLS;
  const row = Math.floor(index / GRID_COLS);
  return {
    x: 16 + col * (CARD_DEFAULT_W + GRID_GAP),
    y: 16 + row * (CARD_DEFAULT_H + GRID_GAP + 20),
  };
}

function DraggableCard({ id, x, y, children }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id });

  const style = {
    position: 'absolute',
    left: x + (transform?.x || 0),
    top: y + (transform?.y || 0),
    zIndex: isDragging ? 999 : 1,
    cursor: isDragging ? 'grabbing' : 'grab',
    userSelect: 'none',
    transition: isDragging ? 'none' : 'box-shadow 0.15s',
  };

  return (
    <div ref={setNodeRef} style={style} {...listeners} {...attributes}>
      {children}
    </div>
  );
}

export default function CanvasView({ items, renderCard, getPositions, savePosition, onReset, canvasHeight = 1200 }) {
  const [positions, setPositions] = useState(() => {
    const saved = getPositions();
    return saved;
  });

  const resolvePosition = useCallback((id, index) => {
    if (positions[id]) return positions[id];
    return gridPosition(index);
  }, [positions]);

  const handleDragEnd = useCallback((event) => {
    const { active, delta } = event;
    if (!active || !delta) return;
    const id = active.id;
    const index = items.findIndex(item => item.id === id);
    const old = resolvePosition(id, index);
    const nx = Math.max(8, old.x + delta.x);
    const ny = Math.max(8, old.y + delta.y);
    setPositions(prev => ({ ...prev, [id]: { x: nx, y: ny } }));
    savePosition(id, nx, ny);
  }, [items, resolvePosition, savePosition]);

  const handleReset = () => {
    setPositions({});
    onReset();
  };

  const maxY = items.reduce((acc, item, i) => {
    const pos = resolvePosition(item.id, i);
    return Math.max(acc, pos.y + CARD_DEFAULT_H + 40);
  }, canvasHeight);

  return (
    <div className="relative">
      <div className="flex justify-end mb-2">
        <button
          onClick={handleReset}
          className="flex items-center gap-1.5 text-xs text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
          title="Reset positions"
        >
          <RotateCcw className="w-3 h-3" />
          Reset layout
        </button>
      </div>
      <DndContext onDragEnd={handleDragEnd}>
        <div
          className="relative w-full rounded-xl border border-dashed border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/30 overflow-hidden"
          style={{ height: maxY }}
        >
          {items.map((item, index) => {
            const pos = resolvePosition(item.id, index);
            return (
              <DraggableCard key={item.id} id={item.id} x={pos.x} y={pos.y}>
                {renderCard(item, index)}
              </DraggableCard>
            );
          })}
        </div>
      </DndContext>
    </div>
  );
}
