import DashboardLayout from "@/components/layouts/dashboard-layout";
import MessagePlatformImg from "@/components/message-platform-image";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useDiscordChannelsQuery,
  useOwnedDiscordGuildsQuery,
} from "@/hooks/connections-hooks";
import { useDeployModeratorMutation } from "@/hooks/moderators-hooks";
import { cn } from "@/lib/utils";
import {
  MessagePlatformType,
  type BaseActionDefinition,
  type DeploymentCreate,
  type DeploymentCreateConf,
  type DiscordConfigResponse,
  type DiscordConfigResponseAllowedActions,
  type DiscordConfigResponseAllowedChannels,
} from "@/openapi";
import { ArrowLeft } from "lucide-react";
import { useState, type FC } from "react";
import { useNavigate, useParams } from "react-router";

interface DeploymentStageProps<T> {
  onNext: (arg: T) => void;
}

type ActionField = {
  name: string;
  type: "number" | "text";
  label?: string;
};

type ActionConfig = {
  type: string;
  fields: ActionField[];
  defaultRequiresApproval: boolean;
};

const AVAILABLE_ACTIONS: ActionConfig[] = [
  {
    type: "mute",
    fields: [{ name: "duration", type: "number", label: "Duration ms (Optional)", }],
    defaultRequiresApproval: false,
  },
  {
    type: "ban",
    fields: [],
    defaultRequiresApproval: true,
  },
  {
    type: "kick",
    fields: [],
    defaultRequiresApproval: false,
  },
];

const LoadingPage: FC = () => {
  return <h1>loading</h1>;
};

const SelectNameCard: FC<DeploymentStageProps<string>> = (props) => {
  const [name, setName] = useState("");

  return (
    <>
      <h4 className="mb-3 font-semibold">Name your Deployment</h4>
      <div className="flex w-full flex-col">
        <div className="flex w-full flex-col gap-4">
          <Input
            id="deployment-name"
            placeholder="e.g. My-Discord-Moderator"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 max-w-sm"
          />

          <Button
            type="button"
            onClick={() => props.onNext(name)}
            disabled={name.trim().length === 0}
            className="w-fit"
          >
            Next
          </Button>
        </div>
      </div>
    </>
  );
};

const SelectActionsCard: FC<
  DeploymentStageProps<DiscordConfigResponseAllowedActions>
> = (props) => {
  const [allowAll, setAllowAll] = useState(false);
  const [allowedActions, setAllowedActions] = useState<{
    [key: string]: {
      requires_approval: boolean;
      params: { [key: string]: string | number };
      enabled: boolean;
    };
  }>(
    AVAILABLE_ACTIONS.reduce((acc, action) => {
      acc[action.type] = {
        requires_approval: action.defaultRequiresApproval,
        params: {},
        enabled: false,
      };
      return acc;
    }, {} as any),
  );

  const handleToggleAction = (actionType: string, checked: boolean) => {
    setAllowAll(false); // Uncheck "Allow All" on fine-tune change
    setAllowedActions((prev) => ({
      ...prev,
      [actionType]: {
        ...prev[actionType],
        enabled: checked,
      },
    }));
  };

  const handleToggleRequiresApproval = (
    actionType: string,
    checked: boolean,
  ) => {
    setAllowedActions((prev) => ({
      ...prev,
      [actionType]: {
        ...prev[actionType],
        requires_approval: checked,
      },
    }));
  };

  const handleParamChange = (
    actionType: string,
    paramName: string,
    value: string,
  ) => {
    setAllowedActions((prev) => ({
      ...prev,
      [actionType]: {
        ...prev[actionType],
        params: {
          ...prev[actionType].params,
          [paramName]: value,
        },
      },
    }));
  };

  const handleAllowAllClick = () => {
    setAllowAll((prev) => !prev);
  };

  const finalizeAndSubmit = () => {
    let finalActions: DiscordConfigResponseAllowedActions;

    if (allowAll) {
      finalActions = ["*"];
    } else {
      finalActions = AVAILABLE_ACTIONS.filter(
        (action) => allowedActions[action.type].enabled,
      ).map((action) => {
        const config = allowedActions[action.type];

        const collectedParams = Object.entries(config.params).reduce(
          (acc, [key, value]) => {
            if (typeof value === "string" && value.trim() !== "") {
              const fieldDef = action.fields.find((f) => f.name === key);
              if (fieldDef?.type === "number") {
                const numVal = parseFloat(value);
                if (!isNaN(numVal)) {
                  acc[key] = numVal;
                  return acc;
                }
              }
              acc[key] = value;
            } else if (typeof value === "number") {
              acc[key] = value;
            }
            return acc;
          },
          {} as Record<string, unknown>,
        );

        const baseAction: BaseActionDefinition = {
          type: action.type,
          requires_approval: config.requires_approval,
          ...collectedParams,
        } as BaseActionDefinition;

        return baseAction;
      });
    }

    props.onNext(finalActions);
  };

  return (
    <div className="flex w-full flex-col">
      <div className="flex flex-col">
        <div className="mb-4 flex items-center justify-between">
          <h4 className="font-semibold">Action Configuration</h4>
          <Button
            variant="outline"
            size="sm"
            className=""
            type="button"
            onClick={handleAllowAllClick}
          >
            {allowAll ? "Allow All (Enabled)" : "Allow All"}
          </Button>
        </div>
        <Accordion
          type="multiple"
          className="w-full overflow-hidden rounded-md border"
          disabled={allowAll}
        >
          {AVAILABLE_ACTIONS.map((action, idx) => (
            <AccordionItem
              value={`item-${idx + 1}`}
              key={action.type}
              className="transition-colors"
            >
              <AccordionTrigger className="flex items-center justify-between px-4 focus:!outline-none">
                <div className="flex items-center gap-2">
                  <Input
                    type="checkbox"
                    className="h-4 w-fit"
                    checked={allowedActions[action.type].enabled}
                    onClick={(e) => e.stopPropagation()} // Prevent accordion toggle
                    onChange={(e) =>
                      handleToggleAction(action.type, e.target.checked)
                    }
                    disabled={allowAll}
                  />
                  <span>{action.type}</span>
                </div>
              </AccordionTrigger>
              <AccordionContent className="bg-secondary border-t p-4">
                <div className="space-y-3">
                  {/* Action-specific fields */}
                  {action.fields.map((field) => (
                    <div key={field.name}>
                      <label
                        htmlFor={`${action.type}-${field.name}`}
                        className="text-sm font-medium"
                      >
                        {field.label ? field.label: field.name.charAt(0).toUpperCase() +
                          field.name.slice(1).replace(/_/g, " ") + " (Optional)"}
                      </label>
                      <Input
                        id={`${action.type}-${field.name}`}
                        type={field.type === "number" ? "number" : "text"}
                        min={field.type === "number" ? 1 : undefined}
                        placeholder="Optional default value"
                        value={
                          allowedActions[action.type].params[field.name] || ""
                        }
                        onChange={(e) =>
                          handleParamChange(
                            action.type,
                            field.name,
                            e.target.value,
                          )
                        }
                        className="mt-1"
                        disabled={
                          !allowedActions[action.type].enabled || allowAll
                        }
                      />
                    </div>
                  ))}

                  {/* Requires Approval checkbox */}
                  <div className="flex w-full items-center justify-start gap-2 pt-2">
                    <Input
                      type="checkbox"
                      id={`${action.type}-requires_approval`}
                      className="h-4 w-fit"
                      checked={allowedActions[action.type].requires_approval}
                      onChange={(e) =>
                        handleToggleRequiresApproval(
                          action.type,
                          e.target.checked,
                        )
                      }
                      disabled={
                        !allowedActions[action.type].enabled || allowAll
                      }
                    />
                    <label
                      htmlFor={`${action.type}-requires_approval`}
                      className="cursor-pointer text-sm font-medium"
                    >
                      Requires Approval
                    </label>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
      <div className="mt-6 flex w-full items-center justify-start">
        <Button
          type="button"
          onClick={finalizeAndSubmit}
          disabled={
            !allowAll && !Object.values(allowedActions).some((a) => a.enabled)
          }
        >
          Confirm Actions
        </Button>
      </div>
    </div>
  );
};

const SelectChannelsCard: FC<
  DeploymentStageProps<DiscordConfigResponseAllowedChannels> & {
    guildId: string;
  }
> = (props) => {
  const discordChannelsQuery = useDiscordChannelsQuery(props.guildId);
  const [selectedChannels, setSelectedChannels] = useState<{
    [key: string]: boolean;
  }>({});

  return (
    <div className="flex w-full flex-col">
      <div className="flex w-full flex-col items-start gap-4">
        {discordChannelsQuery.isFetching ? (
          <Skeleton className="h-32 w-full rounded-lg" />
        ) : (
          <div className="w-full">
            <div className="mb-4 flex w-full items-center justify-between">
              <h4 className="font-semibold">Select Channels</h4>
              <Button
                variant="outline"
                onClick={() => props.onNext(["*"])}
                className="hover:bg-secondary/80 rounded-md px-4 py-2 transition"
              >
                Select All
              </Button>
            </div>

            <div className="flex flex-col gap-2">
              {discordChannelsQuery.data!.map((ch) => {
                const isSelected = ch.id in selectedChannels;

                return (
                  <div
                    key={ch.id}
                    onClick={() =>
                      setSelectedChannels((prev) => {
                        const updated = { ...prev };
                        if (isSelected) delete updated[ch.id];
                        else updated[ch.id] = true;
                        return updated;
                      })
                    }
                    className={cn(
                      "bg-secondary/40 hover:bg-secondary/60 flex h-10 w-full cursor-pointer items-center justify-between rounded-lg border border-gray-700 p-3 transition-all duration-200 hover:shadow-md",
                      isSelected &&
                        "border-green-400 bg-green-500/20 hover:bg-green-500/30",
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className={cn(
                          "h-4 w-4 rounded-full border border-gray-500 transition-colors",
                          isSelected && "border-green-500 bg-green-500",
                        )}
                      ></span>
                      <span className="truncate font-medium text-gray-100">
                        {ch.name}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-6 flex justify-start">
              <Button
                type="button"
                onClick={() =>
                  props.onNext(
                    Object.keys(
                      selectedChannels,
                    ) as DiscordConfigResponseAllowedChannels,
                  )
                }
              >
                Confirm
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const SelectGuildCard: FC<DeploymentStageProps<string>> = (props) => {
  const ownedDiscordGuildsQuery = useOwnedDiscordGuildsQuery();

  return (
    <>
      <h4 className="mb-3 font-semibold">Select Server</h4>
      <div className="flex w-full flex-col">
        <div className="flex w-full flex-wrap items-start justify-start gap-3">
          {ownedDiscordGuildsQuery.isLoading ? (
            <>
              <Skeleton className="h-30 w-30" />
              <Skeleton className="h-30 w-30" />
              <Skeleton className="h-30 w-30" />
            </>
          ) : (
            ownedDiscordGuildsQuery.data?.map((g, idx) => (
              <Card
                key={idx}
                onClick={() => props.onNext(g.id)}
                className="flex h-30 w-30 cursor-pointer flex-col items-center justify-between gap-0 py-3 duration-100 ease-in hover:-translate-y-1 hover:scale-101 hover:border-white"
              >
                <CardContent className="flex w-full items-center justify-center">
                  <div className="bg-secondary/20 flex h-16 w-16 items-center justify-center overflow-hidden rounded-full">
                    {g.icon ? (
                      <img
                        src={g.icon}
                        alt=""
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <div className="bg-secondary h-full w-full"></div>
                    )}
                  </div>
                </CardContent>

                <CardFooter className="flex w-full justify-center">
                  <span className="max-w-[6rem] truncate text-center text-xs font-semibold">
                    {g.name}
                  </span>
                </CardFooter>
              </Card>
            ))
          )}
        </div>
      </div>
    </>
  );
};

const SelectPlatformCard: FC<DeploymentStageProps<MessagePlatformType>> = (
  props,
) => {
  const borderCols = {
    [MessagePlatformType.discord]: "hover:border-purple-400",
  };

  return (
    <>
      <h4 className="mb-3 font-semibold">Select Platform</h4>
      {Object.values(MessagePlatformType).map((v) => (
        <Card
          key={v}
          onClick={() => props.onNext(v)}
          className={cn(
            "relative h-30 w-30 cursor-pointer border duration-200 ease-in-out hover:-translate-y-0.5 hover:scale-101",
            borderCols[v],
          )}
        >
          <CardContent className="flex items-center justify-center">
            <MessagePlatformImg platform={v} className="" />
          </CardContent>
        </Card>
      ))}
    </>
  );
};

const DeployModeratorPage: FC = () => {
  const { moderatorId } = useParams<{ moderatorId: string }>();
  const navigate = useNavigate();

  const [curStage, setCurStage] = useState(1);
  const [maxStages] = useState(5);
  const [deploymentPlatform, setDeploymentPlatform] = useState<
    MessagePlatformType | undefined
  >(undefined);
  const [discordConfigResponse, setDiscordConfigResponse] = useState<
    DiscordConfigResponse | undefined
  >(undefined);

  const [showLoading, setShowLoading] = useState(false);

  const deployMutation = useDeployModeratorMutation();

  const handleDeploy = async (data: DeploymentCreate) => {
    setShowLoading(true);

    deployMutation
      .mutateAsync({
        moderatorId: moderatorId!,
        data,
      })
      .then(() => navigate(`/moderators/${moderatorId}`));
    setShowLoading(false);
  };

  return (
    <DashboardLayout>
      {showLoading && <LoadingPage />}
      <div className="mb-3">
        <div className="mb-3 flex w-full items-center justify-start gap-2">
          <div className="flex items-center justify-start">
            <ArrowLeft
              size={25}
              onClick={
                curStage > 1
                  ? () => setCurStage((prev) => prev - 1)
                  : () => navigate(`/moderators/${moderatorId}`)
              }
              className="text-muted-foreground cursor-pointer"
            />
          </div>
          <h4 className="font-semibold">Deploy</h4>
        </div>

        <div className="flex h-1 w-full gap-3">
          {(() => {
            const els = [];
            for (let i = 0; i < maxStages; i++) {
              els.push(
                <div
                  className={cn(
                    "h-full rounded-md",
                    curStage >= i + 1
                      ? "bg-blue-500 shadow-xs shadow-blue-700"
                      : "bg-neutral-500 shadow-xs shadow-neutral-700",
                  )}
                  style={{ width: `calc(100% / ${maxStages})` }}
                ></div>,
              );
            }
            return els;
          })()}
        </div>
      </div>

      <div className="mb-3">
        <div className="">
          {curStage === 1 && (
            <SelectPlatformCard
              onNext={(arg: MessagePlatformType) => {
                setDeploymentPlatform(arg);
                setCurStage((prev) => prev + 1);
              }}
            />
          )}

          {curStage === 2 && (
            <SelectGuildCard
              onNext={(arg: string) => {
                setDiscordConfigResponse(
                  (prev) =>
                    ({
                      ...(prev ?? {}),
                      guild_id: arg,
                    }) as DiscordConfigResponse,
                );
                setCurStage((prev) => prev + 1);
              }}
            />
          )}

          {curStage === 3 && (discordConfigResponse ?? {}).guild_id && (
            <SelectChannelsCard
              onNext={(arg: DiscordConfigResponseAllowedChannels) => {
                setDiscordConfigResponse(
                  (prev) =>
                    ({
                      ...prev,
                      allowed_channels: arg,
                    }) as DiscordConfigResponse,
                );
                setCurStage((prev) => prev + 1);
              }}
              guildId={discordConfigResponse!.guild_id}
            />
          )}

          {curStage === 4 && (
            <SelectActionsCard
              onNext={(arg: DiscordConfigResponseAllowedActions) => {
                setDiscordConfigResponse(
                  (prev) =>
                    ({
                      ...prev,
                      allowed_actions: arg,
                    }) as DiscordConfigResponse,
                );
                setCurStage((prev) => prev + 1);
              }}
            />
          )}

          {curStage === 5 && (
            <SelectNameCard
              onNext={(arg: string) => {
                handleDeploy({
                  name: arg,
                  platform: deploymentPlatform!,
                  conf: discordConfigResponse as unknown as DeploymentCreateConf,
                });
              }}
            />
          )}
        </div>
      </div>
    </DashboardLayout>
  );
};
export default DeployModeratorPage;
