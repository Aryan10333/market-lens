-- A company can have two actions on the same ex-date, for example BAJFINANCE on
-- 16 Jun 2025: "Bonus 4:1" AND a face value split from Rs 2 to Re 1. The factors
-- multiply (0.2 x 0.5 = 0.1), and the row is then marked 'multiple'.

alter table public.price_adjustments
  drop constraint price_adjustments_action_type,
  add constraint price_adjustments_action_type
    check (action_type in ('bonus', 'split', 'consolidation', 'multiple'));
