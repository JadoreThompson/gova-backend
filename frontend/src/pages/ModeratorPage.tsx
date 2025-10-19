import DashboardLayout from "@/components/layouts/dashboard-layout";
import type { FC } from "react";
import { useParams } from "react-router";

const ModeratorPage: FC = () => {
  const { moderatorId } = useParams() as { moderatorId: string };
  
  return (
    <DashboardLayout>
      <p>{moderatorId}</p>
    </DashboardLayout>
  );
};
export default ModeratorPage;
