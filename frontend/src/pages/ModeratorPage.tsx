import DeploymentsTable from "@/components/deployments-table";
import DashboardLayout from "@/components/layouts/dashboard-layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useModeratorDeploymentsQuery,
  useModeratorQuery,
  useModeratorStatsQuery,
} from "@/hooks/moderators-hooks";
import { type NewMessageChartData } from "@/openapi";
import { Bot } from "lucide-react";
import { useMemo, useState, type FC } from "react";
import { useNavigate, useParams } from "react-router";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const StatsCards: FC<{ totalMessages: number; totalActions: number }> = ({
  totalMessages,
  totalActions,
}) => (
  <div className="mb-6 flex h-30 gap-3">
    <Card className="h-full w-70 gap-2">
      <CardHeader className="mb-0">
        <CardTitle className="text-muted-foreground">
          Total Messages Processed
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold">{totalMessages.toLocaleString()}</p>
      </CardContent>
    </Card>
    <Card className="h-full w-70 gap-2">
      <CardHeader className="mb-0">
        <CardTitle className="text-muted-foreground">
          Total Actions Taken
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold">{totalActions.toLocaleString()}</p>
      </CardContent>
    </Card>
  </div>
);

const MessagesChart: FC<{ chartData: NewMessageChartData[] }> = ({
  chartData,
}) => {
  const flattenedData = useMemo(() => {
    return chartData.map((entry) => ({
      date: entry.date,
      ...entry.counts,
    }));
  }, [chartData]);

  const platforms = useMemo(() => {
    if (flattenedData.length === 0) return [];
    return Object.keys(flattenedData[0]).filter((k) => k !== "date");
  }, [flattenedData]);

  return (
    <Card className="mb-8">
      <CardHeader>
        <CardTitle>Messages Processed (Last 6 Weeks)</CardTitle>
      </CardHeader>
      <CardContent className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={flattenedData}
            barGap={4}
            margin={{ top: 10, right: 20, left: 0, bottom: 10 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#E5E7EB"
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12, fill: "#9CA3AF" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 12, fill: "#9CA3AF" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(255,255,255,0.95)",
                border: "1px solid #E5E7EB",
                borderRadius: "8px",
                fontSize: "13px",
              }}
              labelStyle={{ color: "#374151", fontWeight: 500 }}
            />
            <Legend
              verticalAlign="top"
              align="right"
              wrapperStyle={{ fontSize: "12px", paddingBottom: "8px" }}
            />

            {platforms.map((platform) => {
              let color = "#9CA3AF";

              if (platform.toLowerCase().includes("discord")) color = "#5865F2";
              else if (platform.toLowerCase().includes("telegram"))
                color = "#229ED9";
              else if (platform.toLowerCase().includes("slack"))
                color = "#ECB22E";

              return (
                <Bar
                  key={platform}
                  dataKey={platform}
                  stackId="a"
                  fill={color}
                  radius={
                    platform === platforms[platforms.length - 1]
                      ? [6, 6, 0, 0]
                      : [0, 0, 0, 0]
                  }
                />
              );
            })}
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};

const DeploymentsSection: FC<{
  deployments: any[];
  page: number;
  setPage: (p: number) => void;
  navigate: ReturnType<typeof useNavigate>;
}> = ({ deployments, page, setPage, navigate }) => (
  <DeploymentsTable
    deployments={deployments}
    page={page}
    hasNextPage={false}
    onPrevPage={() => setPage((p) => p - 1)}
    onNextPage={() => setPage((p) => p + 1)}
    onRowClick={(d) => navigate(`/deployments/${d.deployment_id}`)}
  />
);

const ModeratorPage: FC = () => {
  const { moderatorId } = useParams();
  const navigate = useNavigate();

  const [page, setPage] = useState(1);

  const moderatorQuery = useModeratorQuery(moderatorId);
  const moderatorStatsQuery = useModeratorStatsQuery(moderatorId);
  const moderatorDeploymentsQuery = useModeratorDeploymentsQuery(moderatorId, {
    page,
  });

  return (
    <DashboardLayout>
      <div className="mb-6 flex items-center justify-between pt-5">
        {moderatorQuery.isFetching ? (
          <Skeleton />
        ) : (
          <div className="flex items-center gap-2">
            <Bot />
            <h4 className="font-semibold">{moderatorQuery.data?.name}</h4>
          </div>
        )}
        <Button onClick={() => navigate(`/moderators/${moderatorId}/deploy`)}>
          Deploy
        </Button>
      </div>

      <StatsCards
        totalMessages={moderatorStatsQuery.data?.total_messages ?? 0}
        totalActions={moderatorStatsQuery.data?.total_actions ?? 0}
      />
      <MessagesChart
        chartData={moderatorStatsQuery.data?.message_chart ?? []}
      />
      <DeploymentsSection
        deployments={moderatorDeploymentsQuery.data?.data ?? []}
        page={page}
        setPage={setPage}
        navigate={navigate}
      />
    </DashboardLayout>
  );
};

export default ModeratorPage;
