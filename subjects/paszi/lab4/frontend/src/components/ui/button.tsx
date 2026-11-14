import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";

const buttonVariants = cva("", {
    variants: {
        variant: {
            default: "primary",
            secondary: "secondary",
            destructive: "danger",
            link: "text-button",
            plain: "",
        },
    },
    defaultVariants: { variant: "default" },
});

type ButtonProps = ComponentProps<"button"> & VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
};

export function Button({ className, variant, asChild = false, ...props }: ButtonProps) {
    const Component = asChild ? Slot : "button";
    return (
        <Component
            data-slot="button"
            data-variant={variant ?? "default"}
            className={buttonVariants({ variant, className })}
            {...props}
        />
    );
}
