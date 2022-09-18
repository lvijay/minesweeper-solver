/**
 * Play Minesweeper.
 */

import java.awt.Robot;

import static java.nio.charset.StandardCharsets.UTF_8;
import static java.util.stream.Collectors.toUnmodifiableMap;

import java.awt.Dimension;
import java.awt.MouseInfo;
import java.awt.Rectangle;
import java.awt.Toolkit;
import java.io.FileOutputStream;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

import javax.imageio.ImageIO;

import com.sun.net.httpserver.Headers;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.spi.HttpServerProvider;

public class MinesweeperPlayer {
    static abstract class RequestHandler implements HttpHandler {
        private final Robot robot;

        public RequestHandler(Robot robot) {
            Objects.requireNonNull(robot, "robot must not be null");
            this.robot = robot;
        }

        @Override
        public final void handle(HttpExchange exchange) throws IOException {
            Headers headers = exchange.getResponseHeaders();
            URI requestURI = exchange.getRequestURI();

            System.out.println("Request to " + requestURI);
            String query = Optional.ofNullable(requestURI.getQuery())
                    .orElse("");

            try {
                Map<String, String> qparams = Arrays.stream(query.split("&"))
                        .map(kv -> kv.split("="))
                        .filter(kv -> kv.length == 2)
                        .collect(toUnmodifiableMap(kv -> kv[0], kv -> kv[1]));

                System.out.println("URI = " + requestURI);

                var response = handle(qparams, headers);
                byte[] respData = response.getBytes(UTF_8);
                exchange.sendResponseHeaders(getResponseCode(headers), respData.length);
                exchange.getResponseBody()
                        .write(respData);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        protected final void setResponseCode(Headers responseHeaders, int value) {
            responseHeaders.set("X-RESPONSE-CODE", "" + value);
        }

        protected final int getResponseCode(Headers responseHeaders) {
            var vals = responseHeaders.getOrDefault("X-RESPONSE-CODE", List.of("200"));

            return Integer.parseInt(vals.get(0));
        }

        protected Robot robot() { return robot; }

        protected abstract String handle(Map<String, String> qparams, Headers responseHeaders)
                throws IOException;
    }

    static final class MouseMoveHandler extends RequestHandler {
        public MouseMoveHandler(Robot robot) { super(robot); }

        @Override
        protected String handle(Map<String, String> qparams, Headers responseHeaders) {
            int x = Integer.parseInt(qparams.getOrDefault("x", "-1"));
            int y = Integer.parseInt(qparams.getOrDefault("y", "-1"));

            robot().mouseMove(x, y);
            robot().delay(100);
            var location = MouseInfo.getPointerInfo().getLocation();

            responseHeaders.add("Content-Type", "application/json");

            String response = String.format("""
            {
                "x": %d,
                "y": %d
            }
            """, location.x, location.y);

            System.out.println("mouse location = " + response);

            return response;
        }
    }

    static final class ScreenshotHandler extends RequestHandler {
        private final Dimension screenDims;

        public ScreenshotHandler(Robot robot) {
            super(robot);
            screenDims = Toolkit.getDefaultToolkit().getScreenSize();
        }

        @Override
        protected String handle(Map<String, String> qparams, Headers responseHeaders)
                throws IOException {
            var img = robot().createScreenCapture(new Rectangle(screenDims));
            var tempFilePath = Files.createTempFile("minesweeper_screencap", ".png");
            var tempFile = tempFilePath.toFile();

            tempFile.deleteOnExit();

            try (var out = new FileOutputStream(tempFile)) {
                ImageIO.write(img, "PNG", out);
            }

            // could actually just return the file contents
            return tempFile.getAbsolutePath();
        }
    }

    public static void main(String[] args) throws Exception {
        var robot = new Robot();

        var serverProvider = HttpServerProvider.provider();
        int port = 8888;

        HttpServer server = serverProvider.createHttpServer(
                new InetSocketAddress("localhost", port), 10);

        server.createContext("/screencap", new ScreenshotHandler(robot));
        server.createContext("/mousemove", new MouseMoveHandler(robot));
        server.createContext("/stop", exc -> {
            exc.sendResponseHeaders(200, 4);
            exc.getResponseBody().write("Bye\n".getBytes(UTF_8));
            exc.getResponseHeaders().add("Content-Type", "text/plain");

            new Thread(() -> {
                robot.delay(100);
                System.exit(0);
            }).start();
        });

        server.start();

        System.out.println("Listening on " + port);
    }
}
