----------------------------------------------------------------------------------
-- Testbench for alu3
-- Part 1 (0 - 180 ns): hand-picked cases, 15 ns each. Show this part in the waveform.
-- Part 2 (after 180 ns): every a, b and op combination (4 x 64 = 256 cases)
--                      checked against a reference model.
-- The console shows TEST PASSED or the number of errors. Use "Run All".
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity tb_alu3 is
end tb_alu3;

architecture behavior of tb_alu3 is

    component alu3
        Port ( a        : in  STD_LOGIC_VECTOR (2 downto 0);
               b        : in  STD_LOGIC_VECTOR (2 downto 0);
               op       : in  STD_LOGIC_VECTOR (1 downto 0);
               result   : out STD_LOGIC_VECTOR (2 downto 0);
               carry    : out STD_LOGIC;
               zero     : out STD_LOGIC;
               negative : out STD_LOGIC;
               overflow : out STD_LOGIC;
               equal    : out STD_LOGIC);
    end component;

    signal a, b     : STD_LOGIC_VECTOR (2 downto 0) := "000";
    signal op       : STD_LOGIC_VECTOR (1 downto 0) := "00";
    signal result   : STD_LOGIC_VECTOR (2 downto 0);
    signal carry, zero, negative, overflow, equal : STD_LOGIC;

begin

    uut : alu3 port map (a, b, op, result, carry, zero, negative, overflow, equal);

    stim : process
        variable n_err  : integer := 0;
        variable ri, si : integer;
        variable e_res  : STD_LOGIC_VECTOR (2 downto 0);
        variable e_c, e_v, e_eq : STD_LOGIC;

        -- apply one case, wait, compare every output with the reference model
        procedure check (va, vb : in STD_LOGIC_VECTOR (2 downto 0);
                         vop    : in STD_LOGIC_VECTOR (1 downto 0);
                         dt     : in time) is
        begin
            a <= va; b <= vb; op <= vop;
            wait for dt;
            e_c := '0'; e_v := '0';
            case vop is
                when "00" =>
                    ri := to_integer(unsigned(va)) + to_integer(unsigned(vb));
                    si := to_integer(signed(va)) + to_integer(signed(vb));
                    if ri > 7 then e_c := '1'; end if;
                    if si > 3 or si < -4 then e_v := '1'; end if;
                    e_res := std_logic_vector(to_unsigned(ri mod 8, 3));
                when "01" =>
                    ri := to_integer(unsigned(va)) - to_integer(unsigned(vb));
                    si := to_integer(signed(va)) - to_integer(signed(vb));
                    if ri < 0 then e_c := '1'; end if;
                    if si > 3 or si < -4 then e_v := '1'; end if;
                    e_res := std_logic_vector(to_unsigned(ri mod 8, 3));
                when "10" =>
                    e_res := va and vb;
                when others =>
                    e_res := va xor vb;
            end case;
            if va = vb then e_eq := '1'; else e_eq := '0'; end if;
            if result /= e_res or carry /= e_c or overflow /= e_v
               or negative /= e_res(2) or equal /= e_eq
               or (zero = '1') /= (e_res = "000") then
                n_err := n_err + 1;
                report "MISMATCH at " & time'image(now) severity error;
            end if;
        end procedure;

    begin
        -- Part 1: readable cases for the waveform
        check("001", "010", "00", 15 ns);   -- ADD 1 + 2 = 3
        check("011", "001", "00", 15 ns);   -- ADD 3 + 1 = 100   -> overflow, negative
        check("111", "001", "00", 15 ns);   -- ADD 7 + 1 = 000   -> carry, zero
        check("110", "010", "01", 15 ns);   -- SUB 6 - 2 = 100
        check("010", "101", "01", 15 ns);   -- SUB 2 - 5 = 101   -> borrow, overflow
        check("011", "011", "01", 15 ns);   -- SUB 3 - 3 = 000   -> zero, equal
        check("110", "011", "10", 15 ns);   -- AND = 010
        check("101", "010", "10", 15 ns);   -- AND = 000         -> zero
        check("110", "011", "11", 15 ns);   -- XOR = 101
        check("101", "101", "11", 15 ns);   -- XOR = 000         -> zero, equal
        check("100", "000", "00", 15 ns);   -- ADD -4 + 0 = 100  -> negative
        check("000", "000", "00", 15 ns);   -- ADD 0 + 0 = 000   -> zero, equal

        -- Part 2: exhaustive check
        for o in 0 to 3 loop
            for x in 0 to 7 loop
                for y in 0 to 7 loop
                    check(std_logic_vector(to_unsigned(x, 3)),
                          std_logic_vector(to_unsigned(y, 3)),
                          std_logic_vector(to_unsigned(o, 2)), 1 ns);
                end loop;
            end loop;
        end loop;

        if n_err = 0 then
            report "TEST PASSED (268 cases)" severity note;
        else
            report "TEST FAILED, errors = " & integer'image(n_err) severity error;
        end if;
        wait;
    end process;

end behavior;
