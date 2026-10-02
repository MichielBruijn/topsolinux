// Print the managed stack of every thread of a running .NET Framework process, for the debug command.
// usage: clrstack PID (hexadecimal, as winedbg shows it)
using System;
using System.Linq;
using Microsoft.Diagnostics.Runtime;

class Program
{
    static int Main(string[] args)
    {
        if (args.Length != 1) { Console.Error.WriteLine("usage: clrstack PID"); return 1; }
        using var target = DataTarget.AttachToProcess(Convert.ToInt32(args[0], 16), false);
        if (target.ClrVersions.Length == 0) { Console.WriteLine("no .NET runtime in this process"); return 1; }
        var runtime = target.ClrVersions[0].CreateRuntime();
        foreach (var thread in runtime.Threads.Where(t => t.IsAlive))
        {
            Console.WriteLine($"--- thread {thread.OSThreadId:x4} (managed {thread.ManagedThreadId})");
            foreach (var frame in thread.EnumerateStackTrace().Take(80))
                Console.WriteLine($"  {frame.InstructionPointer:x12} {frame.Method?.Signature ?? frame.FrameName ?? "?"}");
        }
        return 0;
    }
}
