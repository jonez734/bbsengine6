-- Thin wrapper over public.manage_priv (manage_priv.sql). Same signature.

create or replace function public.manage_schema_priv(action text, priv text, target_schema text, target_role text)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
    perform public.manage_priv('schema', action, priv, target_schema, target_role);
end
$$;

alter function public.manage_schema_priv(text, text, text, text) owner to zoid6;
grant execute on function public.manage_schema_priv(text, text, text, text) to sysop;
