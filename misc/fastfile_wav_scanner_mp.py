import sys, os
import multiprocessing, queue
import time
import struct

class Worker(multiprocessing.Process):
 
    def __init__(self, work_queue, result_queue, file_list):
 
        # base class initialization
        multiprocessing.Process.__init__(self)
 
        # job management stuff
        self.work_queue = work_queue
        self.result_queue = result_queue
        self.file_list = file_list
        self.kill_received = False
 
    def _extract_wav(self, infile):

        with open(infile, "rb") as f:

            byte = 1
            
            while byte:
                byte = f.read(1)
                    
                if byte in (b'\x80', b'\x44', b'\x22'): #, b'\x11'):
                    f.seek(-1, 1)
                else:
                    continue
                    
                sample_rate = struct.unpack("i", f.read(4))[0]
                
                if sample_rate not in (48000, 44100, 22050): #, 11025):
                    continue
                
                f.seek(20, 1)
                
                # Check for audio indicator, FE FF FF FF means there's sound data
                if f.read(4) != b'\xfe\xff\xff\xff':
                    continue

                f.seek(-32, 1)
                data_len = struct.unpack("i", f.read(4))[0]

                f.seek(4, 1)
                bits_per_sample, channels = struct.unpack("ii", f.read(8))
                
                f.seek(16, 1)
                filename_start = f.tell()
                
                byte = f.read(1)
                while byte != b'\x00':
                    byte = f.read(1)
                    # TODO: limit this loop!
                
                filename_end = f.tell() - 1
                f.seek(filename_start, 0)
                
                filename_len = filename_end - filename_start
                
                filename = f.read(filename_len)
                filename = "C:\\_cod4_sound\\" + filename.decode('ascii').replace("/", "\\")

                f.seek(1, 1)
                
                frame_size = channels * int((bits_per_sample + 7) / 8)
                avg_bits = sample_rate * frame_size
                
                filepath, file = os.path.split(filename)
                print("%i Hz  %s" % (sample_rate, file), end="")
                
                if os.path.exists(filename):
                    print(" > skipped")
                    f.seek(data_len, 1)
                    continue
                
                if not os.path.exists(filepath):
                    os.makedirs(filepath)
                
                with open(filename, "wb") as out:
                    out.write(b"RIFF")
                    out.write(struct.pack("I", (data_len + 36)))
                    out.write(b"WAVEfmt ")
                    out.write(struct.pack("ihhIIhh", 16, 1, channels, sample_rate, avg_bits, frame_size, bits_per_sample))
                    out.write(b"data")
                    out.write(struct.pack("i", data_len))
                    out.write(f.read(data_len))
                    print(" > ok")
                    
    def run(self):
        while not self.kill_received:
 
            # get a task
            try:
                job = self.work_queue.get_nowait()
            except queue.Empty:
                break
            
            # the actual processing
            file = self.file_list[job]
            print("Beginning file %i: %s\n"
                  "------------------------------------------------------------"
                  % ((job + 1), os.path.split(file)[1])
                  )

            start_time = time.clock()
            
            self._extract_wav(file)

            # store the result
            self.result_queue.put("\nFinished file %i in %.1f sec\n" % ((job + 1), (time.clock() - start_time)))


def main():
    
    print("\n------------------------------------------------------------\n"
          "Scan and extract RIFF WAVE audio data from decompressed fastfiles\n"
          "(c) 2012 CoDEmanX\n"
          "------------------------------------------------------------\n")
    
    if not len(sys.argv) > 1:
        print("No files supplied, quitting.")
        return
        
    file_list = []
    
    for arg in sys.argv[1:]:
        if not os.path.isfile(arg):
            continue
        else:
            file_list.append(arg)
            
    num_jobs = len(file_list)
    num_processes = 4
    
    print("Start processing of %i files...\n" % num_jobs)
    
    # run
    # load up work queue
    work_queue = multiprocessing.Queue()
    for job in range(num_jobs):
        work_queue.put(job)
 
    # create a queue to pass to workers to store the results
    result_queue = multiprocessing.Queue()
 
    # spawn workers
    for i in range(num_processes):
        worker = Worker(work_queue, result_queue, file_list)
        worker.start()
 
    # collect the results off the queue
    results = []
    for i in range(num_jobs):
        print(result_queue.get())

if __name__ == "__main__":
    
    start_time = time.clock()

    main()
    
    print("\nDone. Total time: %.1f sec\n\nPress enter to close!" % (time.clock() - start_time))
    input()
