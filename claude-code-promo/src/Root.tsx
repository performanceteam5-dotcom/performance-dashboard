import React from "react";
import { Composition } from "remotion";
import { ClaudeCodePromo } from "./Composition";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="ClaudeCodePromo"
      component={ClaudeCodePromo}
      durationInFrames={450}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{}}
    />
  );
};
