-- Thin wrapper over public.manage_priv (manage_priv.sql). Same signature.

create or replace function public.manage_database_priv(action text, priv text, target_db text, target_role text)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
    perform public.manage_priv('database', action, priv, target_db, target_role);
end
$$;

alter function public.manage_database_priv(text, text, text, text) owner to zoid6;
grant execute on function public.manage_database_priv(text, text, text, text) to sysop;
