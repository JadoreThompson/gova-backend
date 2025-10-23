import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
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
import { useState, type FC } from "react";
import { useNavigate, useParams } from "react-router";
import DashboardLayout from "./layouts/dashboard-layout";
import MessagePlatformImg from "./message-platform-image";
import { Button } from "./ui/button";
import { Card, CardContent, CardFooter } from "./ui/card";
import { Input } from "./ui/input";
import { Skeleton } from "./ui/skeleton";

interface DeploymentStageProps<T> {
  onNext: (arg: T) => void;
}

type ActionField = {
  name: string;
  type: "number" | "text";
};

type ActionConfig = {
  type: string;
  fields: ActionField[];
  defaultRequiresApproval: boolean;
};

const AVAILABLE_ACTIONS: ActionConfig[] = [
  {
    type: "Mute",
    fields: [{ name: "duration_minutes", type: "number" }],
    defaultRequiresApproval: false,
  },
  {
    type: "Ban",
    fields: [{ name: "reason", type: "text" }],
    defaultRequiresApproval: true,
  },
  {
    type: "Kick",
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
    <div className="flex w-full flex-col">
      <h4 className="mb-4 text-xl font-semibold">Name your Deployment</h4>
      <div className="flex w-full flex-col gap-4">
        <div>
          <label htmlFor="deployment-name" className="text-sm font-medium">
            Deployment Name
          </label>
          <Input
            id="deployment-name"
            placeholder="e.g. My-Discord-Moderator"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 max-w-sm"
          />
        </div>
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
              // Attempt to convert to number if type is 'number'
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
          <label className="text-lg font-semibold">Action Configuration</label>
          <Button
            variant={allowAll ? "default" : "outline"}
            size="sm"
            className="w-fit text-xs"
            type="button"
            onClick={handleAllowAllClick}
          >
            {allowAll ? "Allow All (Enabled)" : "Allow All"}
          </Button>
        </div>
        <Accordion
          type="multiple"
          className="w-full border"
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
                        {field.name.charAt(0).toUpperCase() +
                          field.name.slice(1).replace(/_/g, " ")}{" "}
                        (Optional)
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
        {allowAll && (
          <p className="mt-2 text-sm text-gray-500">
            All actions will be allowed with default settings. Disable "Allow
            All" to fine configure.
          </p>
        )}
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
      <div className="flex w-full items-center justify-start">
        {discordChannelsQuery.isFetching ? (
          <Skeleton />
        ) : (
          <div>
            <div className="flex w-full items-center">
              <Button variant="secondary" onClick={() => props.onNext(["*"])}>
                Select All
              </Button>
            </div>
            {discordChannelsQuery.data!.map((ch) => (
              <>
                <div
                  onClick={() =>
                    setSelectedChannels((prev) => {
                      let newChs = { ...(prev ?? {}) };

                      if (ch.id in newChs) {
                        delete newChs[ch.id];
                      } else {
                        newChs[ch.id] = true;
                      }

                      return newChs;
                    })
                  }
                  className="bg-secondary flex w-50 items-center gap-3 border p-1"
                >
                  <span
                    className={cn(
                      "h-5 w-5 rounded-full bg-gray-500",
                      ch.id in selectedChannels && "bg-green-500",
                    )}
                  ></span>
                  <span>{ch.name}</span>
                </div>
              </>
            ))}
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
        )}
      </div>
    </div>
  );
};

const SelectGuildCard: FC<DeploymentStageProps<string>> = (props) => {
  const ownedDiscordGuildsQuery = useOwnedDiscordGuildsQuery();

  return (
    <div className="flex w-full flex-col">
      <div className="flex w-full flex-wrap items-start justify-start gap-3">
        {ownedDiscordGuildsQuery.isLoading ? (
          <>
            <Skeleton className="h-25 w-25" />
            <Skeleton className="h-25 w-25" />
            <Skeleton className="h-25 w-25" />
          </>
        ) : (
          ownedDiscordGuildsQuery.data?.map((g, idx) => (
            <Card
              key={idx}
              onClick={() => {
                props.onNext(g.id);
              }}
              className="flex-shrink-0 cursor-pointer"
            >
              <CardContent>
                <div className="flex h-25 w-25 flex-col gap-2">
                  <div className="flex h-full w-full items-center justify-center overflow-hidden rounded-full">
                    {g.icon ? (
                      <img src={g.icon} alt="" />
                    ) : (
                      <div className="bg-secondary h-full w-full"></div>
                    )}
                  </div>
                </div>
              </CardContent>
              <CardFooter>
                <span className="text-center text-xs font-semibold">
                  {g.name}
                </span>
              </CardFooter>
            </Card>
          ))
        )}
      </div>
    </div>
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
      {Object.values(MessagePlatformType).map((v) => (
        <Card
          key={v}
          onClick={() => props.onNext(v)}
          className={cn(
            "relative h-25 w-25 cursor-pointer border duration-200 ease-in-out hover:-translate-y-0.5 hover:scale-101",
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

const DeployModeratorFlow: FC = () => {
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

    deployMutation.mutateAsync({
      moderatorId: moderatorId!,
      data,
    });
    setShowLoading(false);
  };

  return (
    <DashboardLayout>
      {showLoading && <LoadingPage />}
      <div className="mb-3">
        <h4 className="font-semibold">Deploy</h4>
        <p className="text-muted-foreground"></p>
      </div>

      <main className="mb-3">
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
                  ({ ...(prev ?? {}), guild_id: arg }) as DiscordConfigResponse,
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
                  ({ ...prev, allowed_channels: arg }) as DiscordConfigResponse,
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
                  ({ ...prev, allowed_actions: arg }) as DiscordConfigResponse,
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
      </main>

      {curStage === 1 && (
        <div className="flex w-full items-center justify-start gap-2">
          <Button
            variant={"secondary"}
            type="button"
            onClick={() => navigate(`/moderators/${moderatorId}`)}
          >
            Back
          </Button>
        </div>
      )}

      {curStage > 1 && (
        <div className="flex w-full items-center justify-start gap-2">
          <Button
            variant={"secondary"}
            type="button"
            onClick={() => setCurStage((prev) => prev - 1)}
          >
            Back
          </Button>
        </div>
      )}
    </DashboardLayout>
  );
};
export default DeployModeratorFlow;
