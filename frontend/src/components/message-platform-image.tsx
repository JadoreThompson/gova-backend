import type { MessagePlatformType } from "@/openapi";
import type { FC } from "react";

const MessagePlatformImg: FC<{
  platform: MessagePlatformType;
  className?: string;
}> = (props) => {
  const getSrc = (value: MessagePlatformType): string => {
    switch (value) {
      case "discord":
        return "/src/assets/discord.png";
    }
  };

  return (
    <img
      src={getSrc(props.platform)}
      alt=""
      className={props.className ?? ""}
    />
  );
};

export default MessagePlatformImg;
