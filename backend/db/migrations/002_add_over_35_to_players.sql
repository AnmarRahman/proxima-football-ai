alter table players
add column if not exists over_35 boolean default false;

with latest_season as (
  select player_id, max(season) as max_season
  from player_seasons
  group by player_id
)
update players p
set over_35 = case
  when p.birth_date is null or ls.max_season is null then false
  else extract(year from age(make_date(ls.max_season, 7, 1), p.birth_date)) >= 35
end,
updated_at = now()
from latest_season ls
where ls.player_id = p.id;
