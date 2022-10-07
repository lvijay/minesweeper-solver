/**
 * Play Minesweeper.
 */

import static java.nio.charset.StandardCharsets.US_ASCII;
import static java.nio.charset.StandardCharsets.UTF_8;
import static java.util.stream.Collectors.toUnmodifiableMap;

import java.awt.Dimension;
import java.awt.MouseInfo;
import java.awt.Rectangle;
import java.awt.Robot;
import java.awt.Toolkit;
import java.awt.event.InputEvent;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import javax.imageio.ImageIO;

import com.sun.net.httpserver.Headers;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.spi.HttpServerProvider;

public class MinesweeperPlayer {
    private final Robot robot;

    public MinesweeperPlayer(Robot robot) {
        this.robot = robot;
    }

    abstract class RequestHandler implements HttpHandler {
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

                byte[] respData = handle(qparams, headers);
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

        protected abstract byte[] handle(Map<String, String> qparams, Headers responseHeaders)
                throws IOException;
    }

    private final class MouseMoveHandler extends RequestHandler {
        @Override
        protected byte[] handle(Map<String, String> qparams, Headers responseHeaders) {
            int x = Integer.parseInt(qparams.getOrDefault("x", "-1"));
            int y = Integer.parseInt(qparams.getOrDefault("y", "-1"));

            robot.mouseMove(x, y);
            var location = MouseInfo.getPointerInfo().getLocation();

            responseHeaders.add("Content-Type", "application/json");

            String response = String.format("""
            { "x": %d, "y": %d }
            """, location.x, location.y);

            System.out.println("mouse location = " + response);

            return response.getBytes(US_ASCII);
        }
    }

    private final class MouseClickHandler extends RequestHandler {
        @Override
        protected byte[] handle(Map<String, String> qparams, Headers responseHeaders) {
            robot.mousePress(InputEvent.BUTTON1_DOWN_MASK);
            robot.delay(20);
            robot.mouseRelease(InputEvent.BUTTON1_DOWN_MASK);
            var location = MouseInfo.getPointerInfo().getLocation();

            responseHeaders.add("Content-Type", "application/json");

            String response = String.format("""
            { "x": %d, "y": %d }
            """, location.x, location.y);

            System.out.println("mouse location = " + response);

            return response.getBytes(US_ASCII);
        }
    }

    private final class ScreenshotHandler extends RequestHandler {
        private final Dimension screenDims;

        public ScreenshotHandler() {
            screenDims = Toolkit.getDefaultToolkit().getScreenSize();
        }

        @Override
        protected byte[] handle(Map<String, String> qparams, Headers headers)
                throws IOException {
            int x = Integer.parseInt(qparams.getOrDefault("x", "-1"));
            int y = Integer.parseInt(qparams.getOrDefault("y", "-1"));
            int w = Integer.parseInt(qparams.getOrDefault("w", "-1"));
            int h = Integer.parseInt(qparams.getOrDefault("h", "-1"));

            Rectangle bounds;
            if (x > 0 && y > 0 && w > 0 && h > 0) {
                bounds = new Rectangle(x, y, w, h);
            } else {
                bounds = new Rectangle(screenDims);
            }
            var img = robot.createScreenCapture(bounds);
            int filesize = img.getWidth() * img.getHeight() * 3;
            var out = new ByteArrayOutputStream(filesize);

            headers.add("Content-Type", "image/png");
            ImageIO.write(img, "PNG", out);

            return out.toByteArray();
        }
    }

    public static void main(String[] args) throws Exception {
        var robot = new Robot();
        var serverProvider = HttpServerProvider.provider();
        int port = 8888;
        var server = serverProvider.createHttpServer(
                new InetSocketAddress("localhost", port), 10);

        var player = new MinesweeperPlayer(robot);

        server.createContext("/screencap", player.new ScreenshotHandler());
        server.createContext("/mousemove", player.new MouseMoveHandler());
        server.createContext("/mouseclick", player.new MouseClickHandler());
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
