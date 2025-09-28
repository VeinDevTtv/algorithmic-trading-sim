"use client";

import { motion, useSpring, useTransform } from "framer-motion";
import * as React from "react";

export function AnimatedNumber({ value, className }: { value: number; className?: string }): JSX.Element {
  const spring = useSpring(value, { stiffness: 120, damping: 20, mass: 0.4 });
  const text = useTransform(spring, (v) => v.toFixed(2));
  React.useEffect(() => {
    spring.set(value);
  }, [value, spring]);
  return <motion.span className={className}>{text}</motion.span>;
}


