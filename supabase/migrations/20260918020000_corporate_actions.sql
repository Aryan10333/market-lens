-- Step 1 correction: take splits/bonuses from NSE's corporate actions feed.
--
-- The first version guessed them from prices, assuming NSE publishes an adjusted
-- "previous close" on the ex-date. It does not: on RELIANCE's bonus ex-date
-- (28 Oct 2024) prev_close was still 2655.70 while the share opened at 1337.
-- So the table now stores the official action, its exact ratio, and the ratio we
-- actually observe in the prices, so the two can be compared.

delete from public.price_adjustments;  -- rows found by the old (wrong) rule

alter table public.price_adjustments
  drop column prev_close_published,
  drop column close_before,
  add column action_type    text not null,
  add column description    text not null,          -- NSE's own wording
  add column observed_ratio numeric(14,8),          -- close on ex-date / previous close
  add column source         text not null default 'nse_corporate_actions',
  add constraint price_adjustments_action_type
    check (action_type in ('bonus', 'split', 'consolidation'));

comment on column public.price_adjustments.factor is
  'Multiply prices before ex_date by this: bonus 1:1 = 0.5, split 10->1 = 0.1, consolidation 1->10 = 10';
