import { BrowserRouter, Route, Routes } from "react-router";
import DeploymentsPage from "./pages/DeploymentsPage";
import HomePage from "./pages/HomePage";
import DeploymentPage from "./pages/DeploymentPage";

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
        </Routes>
      </BrowserRouter>
    </>
  );
}

export default App;
