import React from "react";
import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import DeadlineTracker from "./components/DeadlineTracker";
import ManytaskPage from "./components/ManytaskPage";
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
          <Route path="/manytask" element={<ManytaskPage />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
