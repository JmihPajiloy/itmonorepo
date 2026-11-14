import { clsx } from "clsx";
import type { ComponentProps } from "react";

export function Card({ className, ...props }: ComponentProps<"div">) {
    return <div data-slot="card" className={clsx("card", className)} {...props} />;
}
