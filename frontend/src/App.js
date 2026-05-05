import React from "react";
import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import DeadlineTracker from "./components/DeadlineTracker";
import { useFolders } from "./hooks/useFolders";

function Workspace() {
  const foldersApi = useFolders();
  return <DeadlineTracker foldersApi={foldersApi} />;
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Workspace />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
