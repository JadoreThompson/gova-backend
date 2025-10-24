import { BrowserRouter, Route, Routes } from "react-router";
import ConnectionsPage from "./pages/ConnectionsPage";
import DeployModeratorFlow from "./pages/DeployModeratorFlowPage";
import DeploymentPage from "./pages/DeploymentPage";
import DeploymentsPage from "./pages/DeploymentsPage";
import GuidelinesPage from "./pages/GuidelinesPage";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import ModeratorPage from "./pages/ModeratorPage";
import ModeratorsPage from "./pages/ModeratorsPage";
import ProfilePage from "./pages/ProfilePage";
import RegisterPage from "./pages/RegisterPage";

function App() {
  return (
    <>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/deployments" element={<DeploymentsPage />} />
          <Route
            path="/deployments/:deploymentId"
            element={<DeploymentPage />}
          />
          <Route path="/guidelines" element={<GuidelinesPage />} />
          <Route path="/moderators" element={<ModeratorsPage />} />
          <Route path="/moderators/:moderatorId" element={<ModeratorPage />} />
          <Route
            path="/moderators/:moderatorId/deploy"
            element={<DeployModeratorFlow />}
          />
          <Route path="/connections" element={<ConnectionsPage />} />
        </Routes>
      </BrowserRouter>
    </>
  );
}

export default App;
