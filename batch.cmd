start "abra" "python" program_main.py 8801 abra
ping 127.255.255.255 -n 1 -w 1000
start "bobby" "python" program_main.py -c localhost -p 8801 8802 bobby
ping 127.255.255.255 -n 1 -w 1000
start "candy" "python" program_main.py -c localhost -p 8801 8803 candy
ping 127.255.255.255 -n 1 -w 1000
start "danny" "python" program_main.py -c localhost -p 8801 8804 danny
ping 127.255.255.255 -n 1 -w 1000
start "elisa" "python" program_main.py -c localhost -p 8801 8805 elisa
ping 127.255.255.255 -n 1 -w 1000
start "fiona" "python" program_main.py -c localhost -p 8801 8806 fiona
ping 127.255.255.255 -n 1 -w 1000
start "germy" "python" program_main.py -c localhost -p 8801 8807 germy
ping 127.255.255.255 -n 1 -w 1000
start "honne" "python" program_main.py -c localhost -p 8801 8808 honne -e 3
ping 127.255.255.255 -n 1 -w 1000
start "innue" "python" program_main.py -c localhost -p 8801 8809 innue
ping 127.255.255.255 -n 1 -w 1000