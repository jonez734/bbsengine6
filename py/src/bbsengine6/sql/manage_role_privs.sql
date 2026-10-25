-- Thin wrapper over public.manage_priv (manage_priv.sql). Same signature.

create or replace function public.manage_role_privs(role_name text, action text, priv text)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
    perform public.manage_priv('role', action, priv, role_name);
end
$$;

alter function public.manage_role_privs(text, text, text) owner to zoid6;
grant execute on function public.manage_role_privs(text, text, text) to sysop;
