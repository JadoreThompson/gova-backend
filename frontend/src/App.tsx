import { BrowserRouter, Route, Routes } from "react-router";
import ConfirmEmailPage from "./pages/ConfirmEmailPage";
import ConnectionsPage from "./pages/ConnectionsPage";
import ContactUsPage from "./pages/ContactUsPage";
import DeployModeratorPage from "./pages/DeployModeratorPage";
import DeploymentPage from "./pages/DeploymentPage";
import GuidelinesPage from "./pages/GuidelinesPage";
import LoginPage from "./pages/LoginPage";
import ModeratorPage from "./pages/ModeratorPage";
import ModeratorsPage from "./pages/ModeratorsPage";
import PricingPage from "./pages/PricingPage";
import RegisterPage from "./pages/RegisterPage";
import Page500 from "./pages/page500";

function App() {
  return (
    <>
      <BrowserRouter>
        <Routes>
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          {/* <Route path="/profile" element={<ProfilePage />} /> */}
          <Route
            path="/deployments/:deploymentId"
            element={<DeploymentPage />}
          />
          <Route path="/guidelines" element={<GuidelinesPage />} />
          <Route path="/moderators" element={<ModeratorsPage />} />
          <Route path="/moderators/:moderatorId" element={<ModeratorPage />} />
          <Route
            path="/moderators/:moderatorId/deploy"
            element={<DeployModeratorPage />}
          />
          <Route path="/connections" element={<ConnectionsPage />} />
          <Route path="/contact-us" element={<ContactUsPage />} />
          <Route path="/500" element={<Page500 />} />
          <Route path="/confirm-email" element={<ConfirmEmailPage/>} />
        </Routes>
      </BrowserRouter>
    </>
  );
}

export default App;
