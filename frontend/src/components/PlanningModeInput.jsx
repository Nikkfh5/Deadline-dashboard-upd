import React, { useState, useRef, useEffect } from 'react';

const PlanningModeInput = ({ deadline, onUpdate }) => {
  const [value, setValue] = useState(deadline.daysNeeded ? deadline.daysNeeded.toString() : '');
  const timerRef = useRef(null);

  useEffect(() => {
    setValue(deadline.daysNeeded ? deadline.daysNeeded.toString() : '');
  }, [deadline.daysNeeded]);

  const handleChange = (e) => {
    const v = e.target.value;
    setValue(v);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      onUpdate(deadline.id, v);
    }, 300);
  };

  return (
    <input
      type="number"
      min="1"
      max="365"
      value={value}
      onChange={handleChange}
      onClick={(e) => e.stopPropagation()}
      placeholder="days"
      className="w-14 h-7 text-xs text-center rounded-md border border-blue-300 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/30 text-slate-700 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-400 dark:focus:ring-blue-500 transition-all [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
    />
  );
};

export default PlanningModeInput;
