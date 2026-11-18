----------------------------------------------------------------------------------
-- 3-bit ALU with status flags (combinational, no clock)
--
-- All 8 inputs fit on the 8 slide switches, no push buttons needed:
--   a(2:0)  -> SW7..SW5
--   b(2:0)  -> SW4..SW2
--   op(1:0) -> SW1..SW0
-- All 8 outputs go to the 8 LEDs:
--   result(2:0) -> LD2..LD0
--   carry, zero, negative, overflow, equal -> LD3..LD7
--
-- op  operation   result        carry flag
-- 00  ADD         a + b         carry out of bit 2
-- 01  SUB         a - b         '1' = borrow (a < b)
-- 10  AND         a and b       '0'
-- 11  XOR         a xor b       '0'
--
-- zero     = '1' when result = 000
-- negative = result(2)  (sign bit in two's complement, range -4 .. +3)
-- overflow = signed overflow, only for ADD and SUB
-- equal    = '1' when a = b  (works for every op)
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity alu3 is
    Port ( a        : in  STD_LOGIC_VECTOR (2 downto 0);
           b        : in  STD_LOGIC_VECTOR (2 downto 0);
           op       : in  STD_LOGIC_VECTOR (1 downto 0);
           result   : out STD_LOGIC_VECTOR (2 downto 0);
           carry    : out STD_LOGIC;
           zero     : out STD_LOGIC;
           negative : out STD_LOGIC;
           overflow : out STD_LOGIC;
           equal    : out STD_LOGIC);
end alu3;

architecture Behavioral of alu3 is

    -- internal copy of the result, because an "out" port cannot be read
    -- in VHDL-93 and the zero / negative flags need to read it
    signal res : STD_LOGIC_VECTOR (2 downto 0);

begin

    alu_proc : process (a, b, op)
        variable sum4 : unsigned (3 downto 0);   -- one extra bit for the carry
    begin
        -- default values, so every output gets a value in every branch
        -- (this also prevents latches in synthesis)
        res      <= (others => '0');
        carry    <= '0';
        overflow <= '0';

        case op is
            when "00" =>                                     -- ADD
                -- example: 011 + 001 = 100, carry = 0
                --          3 + 1 = 4 does not fit in -4..3 -> overflow = 1
                sum4  := ('0' & unsigned(a)) + ('0' & unsigned(b));
                res   <= std_logic_vector(sum4(2 downto 0));
                carry <= sum4(3);
                -- same signs in, different sign out -> signed overflow
                if a(2) = b(2) and sum4(2) /= a(2) then
                    overflow <= '1';
                end if;

            when "01" =>                                     -- SUB
                -- example: 010 - 101 = 101, borrow -> carry = 1
                --          2 - (-3) = 5 does not fit in -4..3 -> overflow = 1
                sum4  := ('0' & unsigned(a)) - ('0' & unsigned(b));
                res   <= std_logic_vector(sum4(2 downto 0));
                carry <= sum4(3);                            -- borrow
                -- different signs in, result sign differs from a -> overflow
                if a(2) /= b(2) and sum4(2) /= a(2) then
                    overflow <= '1';
                end if;

            when "10" =>                                     -- AND
                -- example: 110 and 011 = 010 (bit by bit)
                res <= a and b;

            when "11" =>                                     -- XOR
                -- example: 110 xor 011 = 101 (1 where the bits differ)
                res <= a xor b;

            when others =>
                res <= (others => '0');
        end case;
    end process;

    -- flags that depend only on the result or the inputs
    result   <= res;
    zero     <= '1' when res = "000" else '0';
    negative <= res(2);
    equal    <= '1' when a = b else '0';

end Behavioral;
