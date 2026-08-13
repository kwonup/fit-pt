import Image from 'next/image'
import { cn } from '@/lib/utils'

type BrandLogoProps = {
  variant?: 'hero' | 'auth' | 'mark'
  className?: string
  decorative?: boolean
}

const VARIANT_STYLES = {
  hero: {
    frame: 'h-56 w-52',
    image: 'left-[-90px] top-[-72px] h-[370px] w-[370px]',
    width: 370,
    height: 370,
    src: '/fitpt-logo.png',
  },
  auth: {
    frame: 'h-40 w-36',
    image: 'left-[-65px] top-[-52px] h-[270px] w-[270px]',
    width: 270,
    height: 270,
    src: '/fitpt-logo.png',
  },
  mark: {
    frame: 'h-[49px] w-16',
    image: 'inset-0 h-full w-full',
    width: 658,
    height: 506,
    src: '/fitpt-logo-pure.png',
  },
} as const

export function BrandLogo({
  variant = 'hero',
  className,
  decorative = false,
}: BrandLogoProps) {
  const styles = VARIANT_STYLES[variant]

  return (
    <span className={cn('relative block shrink-0 overflow-hidden', styles.frame, className)}>
      <Image
        src={styles.src}
        alt={decorative ? '' : '핏피티 로고'}
        width={styles.width}
        height={styles.height}
        priority={variant !== 'mark'}
        aria-hidden={decorative || undefined}
        className={cn('absolute max-w-none object-contain', styles.image)}
      />
    </span>
  )
}
