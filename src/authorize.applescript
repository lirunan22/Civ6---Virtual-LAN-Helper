-- Compiled during packaging; only invoked after explicit compatibility opt-in.
-- The command is built from a bundled helper path and validated IPv4 addresses.
on run argv
    if (count of argv) is not 1 then error "Invalid launcher arguments"
    do shell script (item 1 of argv) with administrator privileges
end run
