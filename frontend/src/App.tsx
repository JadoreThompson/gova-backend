import { BrowserRouter, Route, Routes } from "react-router";
import DeploymentPage from "./pages/DeploymentPage";
import DeploymentsPage from "./pages/DeploymentsPage";
import GuidelinesPage from "./pages/GuidelinesPage";
import HomePage from "./pages/HomePage";
import ModeratorPage from "./pages/ModeratorPage";
import ModeratorsPage from "./pages/ModeratorsPage";

function App() {
  return (
    <>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/deployments" element={<DeploymentsPage />} />
          <Route
            path="/deployment/:deploymentId"
            element={<DeploymentPage />}
          />
          <Route path="/guidelines" element={<GuidelinesPage />} />
          <Route path="/moderators" element={<ModeratorsPage />} />
          <Route path="/moderators/:moderatorId" element={<ModeratorPage />} />
        </Routes>
      </BrowserRouter>
    </>
  );
}

export default App;
