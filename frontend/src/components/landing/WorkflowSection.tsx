import { Card, CardBody, Chip } from '@heroui/react';
import { motion, useMotionTemplate, useMotionValue, useSpring, useTransform } from 'framer-motion';
import type { PointerEvent } from 'react';
import type { TFunction } from 'i18next';
import { Activity, CalendarClock, ListMusic, LucideIcon, PlugZap } from 'lucide-react';
import { workflowSteps } from '../../lib/landing/sections';
import { useTranslation } from 'react-i18next';

const workflowSummaryKeys = [
  'landing_steps_bullet_accounts',
  'landing_steps_bullet_resilience',
  'landing_steps_bullet_growth',
] as const;

const stepIcons: Record<string, LucideIcon> = {
  connect: PlugZap,
  playlist: ListMusic,
  schedule: CalendarClock,
  monitor: Activity,
};

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  show: (index: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: index * 0.08,
      type: 'spring',
      stiffness: 120,
      damping: 18,
    },
  }),
};

type WorkflowCardProps = {
  step: (typeof workflowSteps)[number];
  icon: LucideIcon;
  index: number;
  t: TFunction<'translation'>;
};

const WorkflowCard = ({ step, icon: Icon, index, t }: WorkflowCardProps) => {
  const mouseX = useMotionValue(0.5);
  const mouseY = useMotionValue(0.5);
  const easedX = useSpring(mouseX, { stiffness: 280, damping: 36, mass: 0.3 });
  const easedY = useSpring(mouseY, { stiffness: 280, damping: 36, mass: 0.3 });
  const percentX = useTransform(easedX, (value) => `${(value * 100).toFixed(2)}%`);
  const percentY = useTransform(easedY, (value) => `${(value * 100).toFixed(2)}%`);
  const glowBackground = useMotionTemplate`radial-gradient(200px circle at ${percentX} ${percentY}, rgba(87,205,255,0.3), transparent 70%)`;

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    mouseX.set((event.clientX - bounds.left) / bounds.width);
    mouseY.set((event.clientY - bounds.top) / bounds.height);
  };

  const handlePointerLeave = () => {
    mouseX.set(0.5);
    mouseY.set(0.5);
  };

  return (
    <motion.li
      className="focus-within:ring-1 focus-within:ring-[color:var(--landing-accent-glow)] focus-within:ring-offset-0"
      variants={itemVariants}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, amount: 0.6 }}
      custom={index}
    >
      <motion.div
        className="group relative h-full"
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.99 }}
        transition={{ type: 'spring', stiffness: 220, damping: 24 }}
        onPointerMove={handlePointerMove}
        onPointerLeave={handlePointerLeave}
        role="presentation"
      >
        <motion.span
          aria-hidden
          className="pointer-events-none absolute inset-0 rounded-3xl opacity-0 blur-xl transition-opacity duration-300 group-hover:opacity-100"
          style={{ backgroundImage: glowBackground }}
        />
        <Card
          className="relative h-full border text-left backdrop-blur"
          style={{
            background: 'var(--landing-card-strong-bg)',
            borderColor: 'var(--landing-card-border-strong)',
            boxShadow: 'var(--landing-card-shadow-strong)',
          }}
        >
          <CardBody className="flex h-full flex-col gap-4 overflow-visible">
            <div className="flex items-center justify-between">
              <Chip
                variant="flat"
                radius="full"
                className="text-[0.65rem] font-semibold uppercase tracking-[0.3em]"
                style={{
                  background: 'var(--landing-chip-bg)',
                  color: 'var(--landing-chip-text)',
                  border: '1px solid var(--landing-chip-outline)',
                }}
              >
                {t('landing_step_stage_label', { count: index + 1 })}
              </Chip>
              <Icon
                className="h-6 w-6"
                aria-hidden
                style={{ color: 'var(--landing-accent-glow)' }}
              />
            </div>
            <p
              className="text-xs uppercase tracking-[0.4em]"
              style={{ color: 'var(--landing-text-muted)' }}
            >
              {t(`landing_step_${step.id}_badge`)}
            </p>
            <h3 className="text-lg font-semibold" style={{ color: 'var(--landing-text)' }}>
              {t(step.titleKey)}
            </h3>
            <p className="text-sm" style={{ color: 'var(--landing-text-muted)' }}>
              {t(step.descriptionKey)}
            </p>
          </CardBody>
        </Card>
      </motion.div>
    </motion.li>
  );
};

const compactSteps = [
  'landing_steps_compact_connect',
  'landing_steps_compact_playlist',
  'landing_steps_compact_schedule',
  'landing_steps_compact_launch',
] as const;

const WorkflowSection = () => {
  const { t } = useTranslation();
  const mobileDragLimit = -((workflowSteps.length - 1) * 320);

  return (
    <section
      id="landing-workflow"
      className="space-y-6 rounded-4xl border p-5 backdrop-blur-lg xs:p-7"
      style={{
        background: 'var(--landing-section-bg)',
        borderColor: 'var(--landing-card-border-strong)',
        boxShadow: 'var(--landing-section-shadow)',
        color: 'var(--landing-text)',
      }}
      aria-labelledby="landing-workflow-title"
      data-testid="landing-workflow-section"
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-3 lg:max-w-2xl">
          <h2
            id="landing-workflow-title"
            className="text-2xl font-semibold sm:text-3xl"
            style={{ color: 'var(--landing-heading)' }}
          >
            {t('landing_steps_title')}
          </h2>
          <p className="text-base" style={{ color: 'var(--landing-text-muted)' }}>
            {t('landing_steps_thesis')}
          </p>
          <ul className="space-y-2 text-sm" style={{ color: 'var(--landing-text)' }} aria-label={t('landing_steps_subtitle')}>
            {workflowSummaryKeys.map((key) => (
              <li key={key} className="flex items-start gap-3">
                <span
                  className="mt-1 inline-flex h-2 w-2 rounded-full"
                  aria-hidden
                  style={{ backgroundColor: 'var(--landing-accent-glow)' }}
                />
                <span>{t(key)}</span>
              </li>
            ))}
          </ul>
          <div
            className="rounded-3xl border p-4"
            style={{
              background: 'var(--landing-card-alt)',
              borderColor: 'var(--landing-card-border)',
              boxShadow: 'var(--landing-card-shadow)',
            }}
          >
            <p
              className="text-[0.65rem] font-semibold uppercase tracking-[0.35em]"
              style={{ color: 'var(--landing-text-muted)' }}
            >
              {t('landing_steps_compact_label')}
            </p>
            <ul className="mt-3 space-y-3" data-testid="workflow-compact-list">
              {compactSteps.map((key, index) => (
                <li key={key} className="flex items-center gap-3 text-sm" style={{ color: 'var(--landing-text)' }}>
                  <span
                    className="flex h-8 w-8 items-center justify-center rounded-full text-base font-semibold"
                    style={{
                      backgroundColor: 'var(--landing-pill-bg)',
                      color: 'var(--landing-pill-text)',
                      border: '1px solid var(--landing-pill-border)',
                    }}
                  >
                    {index + 1}
                  </span>
                  <span>{t(key)}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
      <div className="pb-2">
        <div className="relative">
          <div className="md:hidden">
            <motion.ol
              className="flex gap-4"
              drag="x"
              dragConstraints={{ left: mobileDragLimit, right: 0 }}
              dragElastic={0.08}
            >
              {workflowSteps.map((step, index) => (
                <div key={`${step.id}-carousel`} className="w-[82vw] shrink-0">
                  <WorkflowCard
                    step={step}
                    icon={stepIcons[step.id] ?? PlugZap}
                    index={index}
                    t={t}
                  />
                </div>
              ))}
            </motion.ol>
          </div>
          <ol className="relative hidden gap-6 pt-6 md:grid md:grid-cols-2 xl:grid-cols-4">
            {workflowSteps.map((step, index) => (
              <WorkflowCard
                key={step.id}
                step={step}
                icon={stepIcons[step.id] ?? PlugZap}
                index={index}
                t={t}
              />
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
};

export default WorkflowSection;
