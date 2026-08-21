interface BrandIconProps {
  asset: string
  alt: string
  className?: string
}

// research.md Decision 1: real downloaded brand marks (public/icons/connectors/*.svg)
// already carry their own official color baked in — no CSS tinting needed here, unlike
// the lucide-react stand-ins rendered directly by ConnectorIcon.
export function BrandIcon({ asset, alt, className }: BrandIconProps) {
  return <img src={`/icons/connectors/${asset}`} alt={alt} className={className} />
}
